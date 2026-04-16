import argparse
import math
from pathlib import Path
from typing import List, Tuple

import imageio.v3 as iio
import numpy as np
import pywt
from matplotlib import pyplot as plt




def load_grayscale_image(path: str) -> np.ndarray:
    img = iio.imread(path)
    if img.ndim == 3:
        # RGB to gray
        img = 0.299 * img[..., 0] + 0.587 * img[..., 1] + 0.114 * img[..., 2]
    img = img.astype(np.float64)
    return img


def save_image(path: str, img: np.ndarray) -> None:
    out = np.clip(np.round(img), 0, 255).astype(np.uint8)
    iio.imwrite(path, out)


def psnr(clean: np.ndarray, test: np.ndarray, data_range: float = 255.0) -> float:
    mse = np.mean((clean.astype(np.float64) - test.astype(np.float64)) ** 2)
    if mse == 0:
        return float("inf")
    return 10.0 * math.log10((data_range ** 2) / mse)


def add_gaussian_noise(img: np.ndarray, sigma: float, seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    noisy = img + rng.normal(0.0, sigma, size=img.shape)
    return np.clip(noisy, 0, 255)


def normalize_columns(D: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(D, axis=0, keepdims=True) + 1e-12
    return D / norms




def dct_matrix(n: int) -> np.ndarray:
    M = np.zeros((n, n), dtype=np.float64)
    for k in range(n):
        v = np.cos(np.arange(n) * k * math.pi / n)
        if k > 0:
            v = v - np.mean(v)
        v = v / (np.linalg.norm(v) + 1e-12)
        M[:, k] = v
    return M


def build_redundant_dct_dictionary(patch_size: int, atoms_per_dim: int) -> np.ndarray:
    D1 = dct_matrix(atoms_per_dim)
    D1 = D1[:patch_size, :]
    D = np.kron(D1, D1)
    D = normalize_columns(D)
    return D




def extract_patches_2d(img: np.ndarray, patch_size: int, stride: int = 1) -> Tuple[np.ndarray, List[Tuple[int, int]]]:
    h, w = img.shape
    patches = []
    positions = []
    for i in range(0, h - patch_size + 1, stride):
        for j in range(0, w - patch_size + 1, stride):
            patch = img[i:i + patch_size, j:j + patch_size].copy()
            patches.append(patch.reshape(-1))
            positions.append((i, j))
    return np.asarray(patches, dtype=np.float64).T, positions  


def aggregate_patches_2d(
    patches: np.ndarray,
    positions: List[Tuple[int, int]],
    image_shape: Tuple[int, int],
    patch_size: int,
    noisy_reference: np.ndarray | None = None,
    lam: float = 0.0,
) -> np.ndarray:
    h, w = image_shape
    acc = np.zeros((h, w), dtype=np.float64)
    weight = np.zeros((h, w), dtype=np.float64)

    for idx, (i, j) in enumerate(positions):
        patch = patches[:, idx].reshape(patch_size, patch_size)
        acc[i:i + patch_size, j:j + patch_size] += patch
        weight[i:i + patch_size, j:j + patch_size] += 1.0

    if noisy_reference is not None and lam > 0:
        acc += lam * noisy_reference
        weight += lam

    return acc / (weight + 1e-12)




def omp_single(
    D: np.ndarray,
    y: np.ndarray,
    max_sparsity: int | None = None,
    error_thresh: float | None = None,
) -> np.ndarray:
    k = D.shape[1]
    residual = y.copy()
    support: List[int] = []
    alpha = np.zeros(k, dtype=np.float64)

    if max_sparsity is None:
        max_sparsity = min(8, k)

    for _ in range(max_sparsity):
        corr = D.T @ residual
        idx = int(np.argmax(np.abs(corr)))
        if idx in support:
            break
        support.append(idx)

        Ds = D[:, support]
        coeffs, *_ = np.linalg.lstsq(Ds, y, rcond=None)
        residual = y - Ds @ coeffs

        if error_thresh is not None and np.linalg.norm(residual) <= error_thresh:
            break

    if support:
        alpha[np.array(support)] = coeffs
    return alpha


def sparse_code_patches(
    Y: np.ndarray,
    D: np.ndarray,
    max_sparsity: int = 6,
    error_thresh: float | None = None,
) -> np.ndarray:
    num_patches = Y.shape[1]
    A = np.zeros((D.shape[1], num_patches), dtype=np.float64)
    for i in range(num_patches):
        A[:, i] = omp_single(D, Y[:, i], max_sparsity=max_sparsity, error_thresh=error_thresh)
    return A




def ksvd_update(Y: np.ndarray, D: np.ndarray, A: np.ndarray, rng: np.random.Generator) -> Tuple[np.ndarray, np.ndarray]:
    n_atoms = D.shape[1]
    for l in range(n_atoms):
        omega = np.nonzero(np.abs(A[l, :]) > 1e-12)[0]

        if omega.size == 0:
            # reinitialize unused atom from a random patch
            rand_idx = int(rng.integers(0, Y.shape[1]))
            D[:, l] = Y[:, rand_idx] / (np.linalg.norm(Y[:, rand_idx]) + 1e-12)
            continue

        # Residual for the patches that use atom l
        E = Y[:, omega] - D @ A[:, omega] + np.outer(D[:, l], A[l, omega])
        U, s, Vt = np.linalg.svd(E, full_matrices=False)
        D[:, l] = U[:, 0]
        A[l, omega] = s[0] * Vt[0, :]

    D = normalize_columns(D)
    return D, A




def denoise_subband_ksvd(
    subband_noisy: np.ndarray,
    sigma: float,
    wavelet_noise_gain_c: float = 1.15,
    patch_size: int = 8,
    atoms_per_dim: int = 16,
    max_sparsity: int = 6,
    train_iters: int = 5,
    lam: float = 1.0,
    stride: int = 1,
    seed: int = 0,
    literal_paper_constraint: bool = False,
) -> Tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)

    
    D = build_redundant_dct_dictionary(patch_size, atoms_per_dim)
    x_hat = subband_noisy.copy()

    n = patch_size * patch_size
    
    if literal_paper_constraint:
        error_thresh = wavelet_noise_gain_c * sigma
    else:
        error_thresh = wavelet_noise_gain_c * sigma * math.sqrt(n)

    for _ in range(train_iters):
        Y, positions = extract_patches_2d(x_hat, patch_size=patch_size, stride=stride)

    
        A = sparse_code_patches(
            Y=Y,
            D=D,
            max_sparsity=max_sparsity,
            error_thresh=error_thresh,
        )

        # Dictionary update stage
        D, A = ksvd_update(Y, D, A, rng)

    
        Y_denoised = D @ A
        x_hat = aggregate_patches_2d(
            patches=Y_denoised,
            positions=positions,
            image_shape=subband_noisy.shape,
            patch_size=patch_size,
            noisy_reference=subband_noisy,
            lam=lam,
        )

    return x_hat, D




def swk_svd_denoise(
    noisy: np.ndarray,
    sigma: float,
    wavelet: str = "db4",
    wavelet_mode: str = "periodization",
    patch_size: int = 8,
    atoms_per_dim: int = 16,
    max_sparsity: int = 6,
    train_iters: int = 5,
    lam: float = 1.0,
    wavelet_noise_gain_c: float = 1.15,
    stride: int = 1,
    seed: int = 0,
    literal_paper_constraint: bool = False,
) -> Tuple[np.ndarray, dict]:
    # Single-scale 2D DWT: cA, (cH, cV, cD)
    cA, (cH, cV, cD) = pywt.dwt2(noisy, wavelet=wavelet, mode=wavelet_mode)

    A_hat, D_A = denoise_subband_ksvd(
        cA, sigma, wavelet_noise_gain_c, patch_size, atoms_per_dim,
        max_sparsity, train_iters, lam, stride, seed + 1, literal_paper_constraint
    )
    H_hat, D_H = denoise_subband_ksvd(
        cH, sigma, wavelet_noise_gain_c, patch_size, atoms_per_dim,
        max_sparsity, train_iters, lam, stride, seed + 2, literal_paper_constraint
    )
    V_hat, D_V = denoise_subband_ksvd(
        cV, sigma, wavelet_noise_gain_c, patch_size, atoms_per_dim,
        max_sparsity, train_iters, lam, stride, seed + 3, literal_paper_constraint
    )
    D_hat, D_D = denoise_subband_ksvd(
        cD, sigma, wavelet_noise_gain_c, patch_size, atoms_per_dim,
        max_sparsity, train_iters, lam, stride, seed + 4, literal_paper_constraint
    )

    denoised = pywt.idwt2((A_hat, (H_hat, V_hat, D_hat)), wavelet=wavelet, mode=wavelet_mode)
    denoised = denoised[: noisy.shape[0], : noisy.shape[1]]
    denoised = np.clip(denoised, 0, 255)

    dictionaries = {
        "A": D_A,
        "H": D_H,
        "V": D_V,
        "D": D_D,
    }
    return denoised, dictionaries




def dictionary_to_montage(D: np.ndarray, patch_size: int, grid_cols: int | None = None) -> np.ndarray:
    n_atoms = D.shape[1]
    if grid_cols is None:
        grid_cols = int(np.ceil(np.sqrt(n_atoms)))
    grid_rows = int(np.ceil(n_atoms / grid_cols))
    canvas = np.zeros((grid_rows * patch_size, grid_cols * patch_size), dtype=np.float64)

    for idx in range(n_atoms):
        r = idx // grid_cols
        c = idx % grid_cols
        atom = D[:, idx].reshape(patch_size, patch_size)
        atom = atom - atom.min()
        atom = atom / (atom.max() + 1e-12)
        canvas[r * patch_size:(r + 1) * patch_size, c * patch_size:(c + 1) * patch_size] = atom
    return canvas


def save_dictionary_panel(out_dir: Path, dictionaries: dict, patch_size: int) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, D in dictionaries.items():
        montage = dictionary_to_montage(D, patch_size)
        save_image(str(out_dir / f"dictionary_{name}.png"), montage * 255.0)



def main() -> None:
    parser = argparse.ArgumentParser(description="Single-scale Wavelet K-SVD (SWK-SVD) image denoising")

    # Ask user only these two inputs
    parser.add_argument("--image", type=str, required=True, help="Path to clean grayscale image")
    parser.add_argument("--sigma", type=float, required=True, help="Gaussian noise std-dev")

    args = parser.parse_args()

    # Fixed default parameters (logic unchanged)
    wavelet = "db4"
    patch_size = 8
    atoms_per_dim = 16
    max_sparsity = 6
    train_iters = 5
    lam = 1
    noise_gain_c = 1.15
    stride = 1
    seed = 0
    literal_paper_constraint = False

    # Default output folder
    out_dir = Path("outputs")
    out_dir.mkdir(parents=True, exist_ok=True)

    clean = load_grayscale_image(args.image)
    noisy = add_gaussian_noise(clean, sigma=args.sigma, seed=seed)

    denoised, dictionaries = swk_svd_denoise(
        noisy=noisy,
        sigma=args.sigma,
        wavelet=wavelet,
        patch_size=patch_size,
        atoms_per_dim=atoms_per_dim,
        max_sparsity=max_sparsity,
        train_iters=train_iters,
        lam=lam,
        wavelet_noise_gain_c=noise_gain_c,
        stride=stride,
        seed=seed,
        literal_paper_constraint=literal_paper_constraint,
    )

    noisy_psnr = psnr(clean, noisy)
    denoised_psnr = psnr(clean, denoised)

    save_image(str(out_dir / "clean.png"), clean)
    save_image(str(out_dir / "noisy.png"), noisy)
    save_image(str(out_dir / "denoised.png"), denoised)
    save_dictionary_panel(out_dir, dictionaries, patch_size)

    with open(out_dir / "metrics.txt", "w", encoding="utf-8") as f:
        f.write(f"Noisy PSNR: {noisy_psnr:.4f} dB\n")
        f.write(f"Denoised PSNR: {denoised_psnr:.4f} dB\n")
        f.write(f"Wavelet: {wavelet}\n")
        f.write(f"Sigma: {args.sigma}\n")
        f.write(f"Patch size: {patch_size}\n")
        f.write(f"Atoms total: {atoms_per_dim ** 2}\n")
        f.write(f"Max sparsity: {max_sparsity}\n")
        f.write(f"Train iterations: {train_iters}\n")
        f.write(f"Lambda: {lam}\n")
        f.write(f"Noise gain C: {noise_gain_c}\n")
        f.write(f"Stride: {stride}\n")
        f.write(f"Literal paper constraint: {literal_paper_constraint}\n")

    print(f"Noisy PSNR    : {noisy_psnr:.4f} dB")
    print(f"Denoised PSNR : {denoised_psnr:.4f} dB")
    print(f"Saved results to: {out_dir}")

    fig, axes = plt.subplots(1, 3, figsize=(14, 5))
    axes[0].imshow(clean, cmap="gray")
    axes[0].set_title("Clean")
    axes[1].imshow(noisy, cmap="gray")
    axes[1].set_title(f"Noisy ({noisy_psnr:.2f} dB)")
    axes[2].imshow(denoised, cmap="gray")
    axes[2].set_title(f"Denoised ({denoised_psnr:.2f} dB)")
    for ax in axes:
        ax.axis("off")
    plt.tight_layout()
   


if __name__ == "__main__":
    main()