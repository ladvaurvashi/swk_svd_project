import React, { useMemo, useRef, useState } from "react";
import { motion } from "framer-motion";
import { Upload, Play, Image as ImageIcon, Gauge, BookOpen, Layers, Sparkles, SlidersHorizontal, Info, Download, FolderOpen, RefreshCw } from "lucide-react";

const Card = ({ children, className = "" }) => (
  <div className={`bg-white/90 backdrop-blur border border-slate-200 rounded-3xl shadow-sm ${className}`}>{children}</div>
);

const SectionTitle = ({ icon: Icon, title, subtitle }) => (
  <div className="flex items-start gap-3 mb-4">
    <div className="p-2 rounded-2xl bg-slate-100 border border-slate-200">
      <Icon className="w-5 h-5 text-slate-700" />
    </div>
    <div>
      <h2 className="text-xl font-semibold text-slate-900">{title}</h2>
      {subtitle ? <p className="text-sm text-slate-600 mt-1">{subtitle}</p> : null}
    </div>
  </div>
);

const StatPill = ({ label, value }) => (
  <div className="px-4 py-3 rounded-2xl bg-slate-50 border border-slate-200 min-w-[120px]">
    <div className="text-xs uppercase tracking-wide text-slate-500">{label}</div>
    <div className="text-lg font-semibold text-slate-900 mt-1">{value}</div>
  </div>
);

const ImagePanel = ({ title, src, caption, alt = title }) => (
  <Card className="overflow-hidden h-full">
    <div className="px-5 py-4 border-b border-slate-200 flex items-center justify-between">
      <h3 className="font-semibold text-slate-900">{title}</h3>
      <ImageIcon className="w-4 h-4 text-slate-500" />
    </div>
    <div className="p-4">
      <div className="aspect-square rounded-2xl bg-slate-100 border border-dashed border-slate-300 flex items-center justify-center overflow-hidden">
        {src ? (
          <img src={src} alt={alt} className="w-full h-full object-contain" />
        ) : (
          <div className="text-center px-4 text-slate-500">
            <ImageIcon className="w-8 h-8 mx-auto mb-2" />
            <p className="text-sm">Image will appear here</p>
          </div>
        )}
      </div>
      {caption ? <p className="text-sm text-slate-600 mt-3 leading-6">{caption}</p> : null}
    </div>
  </Card>
);

const DictionaryPanel = ({ title, src, explanation }) => (
  <Card className="overflow-hidden h-full">
    <div className="px-5 py-4 border-b border-slate-200">
      <h3 className="font-semibold text-slate-900">{title}</h3>
    </div>
    <div className="p-4">
      <div className="aspect-square rounded-2xl bg-slate-100 border border-slate-200 flex items-center justify-center overflow-hidden">
        {src ? (
          <img src={src} alt={title} className="w-full h-full object-contain" />
        ) : (
          <div className="text-center px-4 text-slate-500">
            <Layers className="w-8 h-8 mx-auto mb-2" />
            <p className="text-sm">Dictionary visualization will appear here</p>
          </div>
        )}
      </div>
      <p className="text-sm text-slate-600 mt-3 leading-6">{explanation}</p>
    </div>
  </Card>
);

const TeachingNote = ({ title, body }) => (
  <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
    <h4 className="font-medium text-slate-900">{title}</h4>
    <p className="text-sm text-slate-600 mt-2 leading-6">{body}</p>
  </div>
);

const sigmaExplanation = (sigma) => {
  if (sigma <= 20) {
    return "Low noise. Students can still see the house structure clearly. This is a good setting to explain what gentle Gaussian noise looks like.";
  }
  if (sigma <= 40) {
    return "Moderate noise. Edges start getting disturbed. This is a useful level to explain why sparse representation helps preserve structure while reducing random variation.";
  }
  if (sigma <= 60) {
    return "Strong noise. The image becomes much blurrier and more corrupted; a lower sigma means the denoiser has an easier job, while a higher sigma makes the difference between noisy and cleaned results more visible.";
  }
  return "Very strong noise. The noisy image becomes hard to read directly, so the denoised result and learned dictionaries become excellent teaching visuals for your class.";
};

export default function KSVDTeachingDashboard() {
  const fileInputRef = useRef(null);
  const [sigma, setSigma] = useState(50);
  const [selectedFile, setSelectedFile] = useState(null);
  const [inputPreview, setInputPreview] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);

  const teachingSummary = useMemo(() => sigmaExplanation(sigma), [sigma]);

  const handleFileChange = (event) => {
    const file = event.target.files?.[0];
    if (!file) return;
    setSelectedFile(file);
    setResult(null);
    setError("");
    const objectUrl = URL.createObjectURL(file);
    setInputPreview(objectUrl);
  };

  const handleSigmaSlider = (event) => {
    setSigma(Number(event.target.value));
  };

  const handleSigmaNumber = (event) => {
    const value = Number(event.target.value);
    if (Number.isNaN(value)) return;
    if (value < 1) {
      setSigma(1);
      return;
    }
    if (value > 100) {
      setSigma(100);
      return;
    }
    setSigma(value);
  };

  const resetAll = () => {
    setSigma(50);
    setSelectedFile(null);
    setInputPreview("");
    setResult(null);
    setError("");
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const runDenoising = async () => {
    if (!selectedFile) {
      setError("Please upload an input image first.");
      return;
    }

    setLoading(true);
    setError("");

    try {
      const formData = new FormData();
      formData.append("image", selectedFile);
      formData.append("sigma", String(sigma));

      // Backend contract:
      // POST /api/denoise
      // returns JSON:
      // {
      //   noisy_psnr: number,
      //   denoised_psnr: number,
      //   clean_image: string,
      //   noisy_image: string,
      //   denoised_image: string,
      //   dictionaries: { A: string, H: string, V: string, D: string },
      //   metrics_text?: string
      // }
      const response = await fetch("http://localhost:5000/api/denoise", {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        const text = await response.text();
        throw new Error(text || "Failed to run denoising.");
      }

      const data = await response.json();
      setResult(data);
    } catch (err) {
      setError(err.message || "Something went wrong while processing the image.");
    } finally {
      setLoading(false);
    }
  };

  const downloadIfAvailable = (url, filename) => {
    if (!url) return;
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    link.click();
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-slate-100 text-slate-900">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.35 }}
          className="mb-8"
        >
          <div className="rounded-[28px] bg-slate-900 text-white p-6 md:p-8 shadow-xl overflow-hidden relative">
            <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,rgba(255,255,255,0.16),transparent_30%)]" />
            <div className="relative z-10 grid md:grid-cols-[1.4fr_0.8fr] gap-6 items-center">
              <div>
                <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/10 border border-white/10 text-xs tracking-wide uppercase mb-4">
                  <Sparkles className="w-4 h-4" />
                  Wavelet + K-SVD
                </div>
                <h1 className="text-3xl md:text-4xl font-bold leading-tight">
                  Interactive SWK-SVD Demo for Image Denoising
                </h1>
                <p className="mt-4 text-slate-200 max-w-3xl leading-7">
                  Upload an image, change the sigma value with a slider or direct input,
                  and see how noise changes the image, how denoising works, and what each learned dictionary means.
                </p>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <StatPill label="Wavelet" value="db4" />
                <StatPill label="Patch Size" value="8 × 8" />
                <StatPill label="Atoms" value="256" />
                <StatPill label="Mode" value="Single-scale" />
              </div>
            </div>
          </div>
        </motion.div>

        <div className="grid xl:grid-cols-[380px_1fr] gap-6">
          <div className="space-y-6">
            <Card className="p-5">
              <SectionTitle
                icon={SlidersHorizontal}
                title="Experiment Controls"
                subtitle="Only the classroom-friendly inputs are exposed. The K-SVD logic stays unchanged."
              />

              <div className="space-y-5">
                <div>
                  <label className="text-sm font-medium text-slate-700 mb-2 block">Input image</label>
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept="image/*"
                    onChange={handleFileChange}
                    className="hidden"
                  />
                  <button
                    onClick={() => fileInputRef.current?.click()}
                    className="w-full rounded-2xl border border-dashed border-slate-300 bg-slate-50 hover:bg-slate-100 transition p-5 text-left"
                  >
                    <div className="flex items-center gap-3">
                      <div className="p-3 rounded-2xl bg-white border border-slate-200">
                        <Upload className="w-5 h-5 text-slate-700" />
                      </div>
                      <div>
                        <div className="font-medium text-slate-900">Upload teaching image</div>
                        <div className="text-sm text-slate-600 mt-1">
                          {selectedFile ? selectedFile.name : "Choose a grayscale or RGB image. RGB will be converted to grayscale."}
                        </div>
                      </div>
                    </div>
                  </button>
                </div>

                <div>
                  <label className="text-sm font-medium text-slate-700 mb-2 block">Sigma (noise level)</label>
                  <div className="grid grid-cols-[1fr_90px] gap-3 items-center">
                    <input
                      type="range"
                      min={1}
                      max={100}
                      value={sigma}
                      onChange={handleSigmaSlider}
                      className="w-full"
                    />
                    <input
                      type="number"
                      min={1}
                      max={100}
                      value={sigma}
                      onChange={handleSigmaNumber}
                      className="w-full rounded-2xl border border-slate-300 px-3 py-2.5 outline-none focus:ring-2 focus:ring-slate-300"
                    />
                  </div>
                  <div className="mt-3 rounded-2xl bg-slate-50 border border-slate-200 p-3 text-sm text-slate-600 leading-6">
                    <div className="flex items-center gap-2 text-slate-900 font-medium mb-1">
                      <Gauge className="w-4 h-4" />
                      Sigma explanation
                    </div>
                    {teachingSummary}
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <button
                    onClick={runDenoising}
                    disabled={loading}
                    className="rounded-2xl bg-slate-900 text-white px-4 py-3 font-medium hover:bg-slate-800 transition disabled:opacity-60 flex items-center justify-center gap-2"
                  >
                    {loading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
                    {loading ? "Processing" : "Run Demo"}
                  </button>
                  <button
                    onClick={resetAll}
                    className="rounded-2xl border border-slate-300 bg-white px-4 py-3 font-medium hover:bg-slate-50 transition flex items-center justify-center gap-2"
                  >
                    <RefreshCw className="w-4 h-4" />
                    Reset
                  </button>
                </div>

                {error ? (
                  <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
                    {error}
                  </div>
                ) : null}
              </div>
            </Card>
          </div>

          <div className="space-y-6">
            <div className="grid lg:grid-cols-4 gap-6">
              <ImagePanel
                title="Input / Clean Preview"
                src={result?.clean_image || inputPreview}
                caption="Uploaded image used as the source for the experiment. If the backend returns a clean image path, it is shown here."
              />
              <ImagePanel
                title="Noisy Image"
                src={result?.noisy_image}
                caption={`Gaussian noise is added using sigma = ${sigma}. As sigma increases, random intensity fluctuation becomes more visible.`}
              />
              <ImagePanel
                title="K-SVD Only Denoised"
                src={result?.ksvd_only_image}
                caption="This is the plain K-SVD result without wavelet decomposition. It uses direct patch denoising with a DCT-initialized dictionary."
              />
              <ImagePanel
                title="Denoised Image"
                src={result?.denoised_image}
                caption="This result should become especially meaningful at stronger noise levels, where wavelet-domain sparse denoising is easier to appreciate visually."
              />
            </div>

            <Card className="p-5">
              <SectionTitle
                icon={Info}
                title="Live Result Summary"

              />

              <div className="flex flex-wrap gap-3 mb-4">
                <StatPill label="Sigma" value={sigma} />
                <StatPill label="Noisy PSNR" value={result?.noisy_psnr ? `${Number(result.noisy_psnr).toFixed(2)} dB` : "—"} />
                <StatPill label="K-SVD Only PSNR" value={result?.ksvd_only_psnr ? `${Number(result.ksvd_only_psnr).toFixed(2)} dB` : "—"} />
                <StatPill label="Denoised PSNR" value={result?.denoised_psnr ? `${Number(result.denoised_psnr).toFixed(2)} dB` : "—"} />
                <StatPill label="Status" value={result ? "Completed" : loading ? "Running" : "Waiting"} />
              </div>

              

              {result?.metrics_text ? (
                <div className="mt-4 rounded-2xl bg-slate-50 border border-slate-200 p-4">
                  <div className="text-sm font-medium text-slate-900 mb-2">Metrics file preview</div>
                  <pre className="text-xs text-slate-700 whitespace-pre-wrap leading-6">{result.metrics_text}</pre>
                </div>
              ) : null}
            </Card>

            <div>
              <SectionTitle
                icon={Layers}
                title="Learned Dictionaries"
                
              />
              <div className="grid md:grid-cols-2 xl:grid-cols-4 gap-6">
                <DictionaryPanel
                  title="A Dictionary"
                  src={result?.dictionaries?.A}
                  explanation="Approximation-band atoms. These often capture smoother or larger-scale intensity patterns."
                />
                <DictionaryPanel
                  title="H Dictionary"
                  src={result?.dictionaries?.H}
                  explanation="Horizontal-detail atoms. These often respond to horizontal structures or direction-sensitive detail."
                />
                <DictionaryPanel
                  title="V Dictionary"
                  src={result?.dictionaries?.V}
                  explanation="Vertical-detail atoms. These often capture vertical edges and related structures."
                />
                <DictionaryPanel
                  title="D Dictionary"
                  src={result?.dictionaries?.D}
                  explanation="Diagonal-detail atoms. These are useful when discussing diagonal transitions, corners, and textured components."
                />
              </div>
              <div className="mt-6">
                <h3 className="text-lg font-semibold text-slate-900 mb-4">K-SVD Only Dictionary</h3>
                <DictionaryPanel
                  title="K-SVD Only Dictionary"
                  src={result?.ksvd_only_dictionary}
                  explanation="This is the dictionary learned directly from image patches without wavelet decomposition. It shows the atoms used by plain K-SVD."
                />
              </div>
            </div>

            <Card className="p-5">
              <SectionTitle
                icon={FolderOpen}
                title="Downloads"
               
              />
              <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-3">
                <button
                  onClick={() => downloadIfAvailable(result?.noisy_image, "noisy.png")}
                  className="rounded-2xl border border-slate-300 bg-white px-4 py-3 hover:bg-slate-50 transition flex items-center justify-center gap-2"
                >
                  <Download className="w-4 h-4" />
                  Noisy
                </button>
                <button
                  onClick={() => downloadIfAvailable(result?.denoised_image, "denoised.png")}
                  className="rounded-2xl border border-slate-300 bg-white px-4 py-3 hover:bg-slate-50 transition flex items-center justify-center gap-2"
                >
                  <Download className="w-4 h-4" />
                  Denoised
                </button>
                <button
                  onClick={() => downloadIfAvailable(result?.dictionaries?.A, "dictionary_A.png")}
                  className="rounded-2xl border border-slate-300 bg-white px-4 py-3 hover:bg-slate-50 transition flex items-center justify-center gap-2"
                >
                  <Download className="w-4 h-4" />
                  Dictionary A
                </button>
                <button
                  onClick={() => downloadIfAvailable(result?.dictionaries?.H, "dictionary_H.png")}
                  className="rounded-2xl border border-slate-300 bg-white px-4 py-3 hover:bg-slate-50 transition flex items-center justify-center gap-2"
                >
                  <Download className="w-4 h-4" />
                  Dictionary H
                </button>
              </div>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
}
