<img width="307" height="307" alt="noisy" src="https://github.com/user-attachments/assets/36e139a2-3462-4ca3-96c9-0d7f8ce0b904" /><img width="307" height="307" alt="noisy" src="https://github.com/user-attachments/assets/84ebe597-b346-436c-8d10-f3c050d66fa2" /><img width="381" height="382" alt="image" src="https://github.com/user-attachments/assets/da61d0e7-6da3-471e-9a88-86eb9ff3b766" /># Image Denoising using K-SVD and Wavelet (SWK-SVD)

An interactive project for **image denoising** using:

- **K-SVD (Dictionary Learning)**
- **Wavelet Transform + K-SVD (SWK-SVD)**
- **React Dashboard for Visualization**

This project demonstrates how **multi-scale decomposition + sparse representation** improves image denoising, especially at high noise levels.

---

# How to Run the Project

## Clone the repository

```bash
git clone https://github.com/ladvaurvashi/swk_svd_project.git
cd swk_svd_project

pip install numpy matplotlib scikit-image pywavelets imageio

# Run Denoising Script
python swk_svd_repro.py --image data/house.png --sigma 50

## Run Backend & Frontend

👉 You must run them in **two separate terminals**

### Terminal 1 — Run Backend (Flask API)

```bash
cd backend
python app.py

### Terminal 2 — Run Frontend (React Dashboard)
cd frontend
npm install
npm run dev

## What We Have Done in This Project

### 1. **K-SVD (Dictionary Learning)**

- The image is divided into **small patches (8×8)**  
- Each patch is represented using a **sparse combination of dictionary atoms**  
- The dictionary is learned using the **K-SVD algorithm**  
- The denoised image is reconstructed by **aggregating all patches**

---

### 2. **Wavelet + K-SVD (SWK-SVD)**

This method improves K-SVD using **wavelet decomposition**.

#### Step 1: **Wavelet Decomposition**

The image is split into four subbands:

- **cA** – Approximation (smooth component)  
- **cH** – Horizontal details  
- **cV** – Vertical details  
- **cD** – Diagonal details  

---

#### Step 2: **Dictionary Learning per Subband**

Separate dictionaries are learned for each subband:

- **D_A** – Smooth structures  
- **D_H** – Horizontal edges  
- **D_V** – Vertical edges  
- **D_D** – Diagonal textures  

---

#### Step 3: **Denoising and Reconstruction**

- Each subband is denoised using **K-SVD**  
- The final image is reconstructed using **inverse wavelet transform**

---

## Key Features

- Adjustable **noise level (sigma)**  
- Patch-based **sparse representation**  
- **DCT-based dictionary initialization**  
- Visualization of **learned dictionaries**  
- Multiple **evaluation metrics**

---

## Evaluation Metrics

The performance of the methods is evaluated using:

- **PSNR (Peak Signal-to-Noise Ratio)**  
- **SSIM (Structural Similarity Index)**  
- **MSE (Mean Squared Error)**  
- **MAE (Mean Absolute Error)**  

---

## Observations and Results

### Low Noise (Small Sigma)

- K-SVD performs well  
- Wavelet decomposition provides limited improvement  

---

### High Noise (Large Sigma)

- SWK-SVD performs better  
- Improved handling of:
  - edges  
  - textures  
  - smooth regions  

---

## Key Insight

K-SVD operates on full image patches,  
while SWK-SVD works on **multi-scale components**,  
which makes it more effective for **high noise levels**.

---

## Results

### Original Image
<img width="307" height="307" alt="clean" src="https://github.com/user-attachments/assets/6aa11763-b7a7-4e12-a5ee-aadf9713e2ae" />


### Noisy Image
<img width="307" height="307" alt="noisy" src="https://github.com/user-attachments/assets/5180ee70-1ecf-4367-9d87-f893efef5de1" />


### K-SVD Only Denoised Image
<img width="307" height="307" alt="ksvd_only_denoised" src="https://github.com/user-attachments/assets/877e8316-a651-466c-afdb-40d1f5985d08" />


### SWK-SVD Denoised Image
<img width="307" height="307" alt="denoised" src="https://github.com/user-attachments/assets/76d569d9-8bf4-47dd-9208-73a57b1bf6b4" />


### K-SVD Dictionary
<img width="128" height="128" alt="ksvd_only_dictionary" src="https://github.com/user-attachments/assets/fca1155f-1ff2-41b7-9f04-982d74dc3d8a" />

##**D_A** Dictionary
<img width="128" height="128" alt="dictionary_A" src="https://github.com/user-attachments/assets/f91ec059-003e-450c-afb9-3a9b8fe3430d" />

##**D_H** Dictionary
<img width="128" height="128" alt="dictionary_D" src="https://github.com/user-attachments/assets/ab2d4436-aa15-4d99-b0a3-01dd8edb5b64" />

##**D_V** Dictionary
<img width="128" height="128" alt="dictionary_H" src="https://github.com/user-attachments/assets/650f0c30-8efc-4e16-a2dd-8c2aef72a922" />

##**D_D** Dictionary
<img width="128" height="128" alt="dictionary_V" src="https://github.com/user-attachments/assets/8da77f80-fe2a-4a78-92cc-d6add0ede81d" />

## Sample Metrics Comparison

| Method         | PSNR (dB) | SSIM |
|---------------|----------|------|
| Noisy Image   | 14.71    | 0.25 |
| K-SVD Only    | 24.98    | 0.78 |
| SWK-SVD       | 25.90    | 0.82 |

---

## Why Wavelet + K-SVD Works Better

- Separates image into **frequency components**  
- Learns **specialized dictionaries for each component**  
- Better preservation of:
  - structural information  
  - edges  
  - textures  

---

## Tech Stack

- Python (NumPy, PyWavelets, Scikit-Image)  
- React (Frontend Dashboard)  
- Matplotlib (Visualization)

## Future Work

- One important future direction is to make the **sparsity level learnable and patch-dependent**.
- In the current system, a fixed sparsity constraint is used for all patches, which may not be optimal because different patches have different structural complexity.
- Smooth regions may be represented using only a few atoms, while textured or edge-rich regions may require a larger number of atoms.
- A future model can be designed to predict the optimal sparsity level for each patch dynamically.
- This adaptive sparsity strategy may improve denoising quality, preserve structure more effectively, and reduce unnecessary computation.


