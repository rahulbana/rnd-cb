import React, { useEffect, useState } from "react";
import { fetchOptions, generate, regenerateSection } from "./api.js";
import ResultCard from "./ResultCard.jsx";

const DEFAULT_PRODUCT = {
  product_name: "Wireless Headphones",
  featuresText: "Bluetooth 5.3\n40-hour battery\nNoise cancellation\nFoldable",
  category: "",
  target_audience: "",
  keywordsText: "",
};

export default function App() {
  const [product, setProduct] = useState(DEFAULT_PRODUCT);
  const [style, setStyle] = useState("professional");
  const [length, setLength] = useState("medium");
  const [numVariants, setNumVariants] = useState(1);
  const [options, setOptions] = useState({ styles: [], lengths: [] });

  const [variants, setVariants] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    fetchOptions()
      .then(setOptions)
      .catch(() => {});
  }, []);

  function buildProductPayload() {
    return {
      product_name: product.product_name.trim(),
      features: product.featuresText
        .split("\n")
        .map((f) => f.replace(/^[-*]\s*/, "").trim())
        .filter(Boolean),
      category: product.category.trim(),
      target_audience: product.target_audience.trim(),
      keywords: product.keywordsText
        .split(",")
        .map((k) => k.trim())
        .filter(Boolean),
    };
  }

  function buildConfig() {
    return { style, length, num_variants: Number(numVariants) };
  }

  async function onGenerate(e) {
    e.preventDefault();
    if (!product.product_name.trim()) {
      setError("Please enter a product name.");
      return;
    }
    setError("");
    setLoading(true);
    setVariants([]);
    try {
      const data = await generate(buildProductPayload(), buildConfig());
      setVariants(data.variants);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function onRegenerate(variantIndex, section) {
    try {
      const data = await regenerateSection(buildProductPayload(), buildConfig(), section);
      setVariants((prev) =>
        prev.map((v, i) => (i === variantIndex ? { ...v, [section]: data.value } : v))
      );
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <div className="layout">
      <aside className="panel form-panel">
        <h1>🛍️ Product Description Generator</h1>
        <p className="subtitle">AI-powered e-commerce copy with structured output.</p>

        <form onSubmit={onGenerate}>
          <label>
            Product name
            <input
              type="text"
              value={product.product_name}
              onChange={(e) => setProduct({ ...product, product_name: e.target.value })}
              placeholder="Wireless Headphones"
            />
          </label>

          <label>
            Features (one per line)
            <textarea
              rows={5}
              value={product.featuresText}
              onChange={(e) => setProduct({ ...product, featuresText: e.target.value })}
              placeholder={"Bluetooth 5.3\n40-hour battery"}
            />
          </label>

          <label>
            Category (optional)
            <input
              type="text"
              value={product.category}
              onChange={(e) => setProduct({ ...product, category: e.target.value })}
              placeholder="Electronics"
            />
          </label>

          <label>
            Target audience (optional)
            <input
              type="text"
              value={product.target_audience}
              onChange={(e) => setProduct({ ...product, target_audience: e.target.value })}
              placeholder="Commuters and travelers"
            />
          </label>

          <label>
            Seed SEO keywords (comma separated, optional)
            <input
              type="text"
              value={product.keywordsText}
              onChange={(e) => setProduct({ ...product, keywordsText: e.target.value })}
              placeholder="wireless headphones, noise cancelling"
            />
          </label>

          <div className="row">
            <label>
              Writing style
              <select value={style} onChange={(e) => setStyle(e.target.value)}>
                {options.styles.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
            </label>

            <label>
              Length
              <select value={length} onChange={(e) => setLength(e.target.value)}>
                {options.lengths.map((l) => (
                  <option key={l} value={l}>
                    {l}
                  </option>
                ))}
              </select>
            </label>

            <label>
              Variants
              <select value={numVariants} onChange={(e) => setNumVariants(e.target.value)}>
                {[1, 2, 3, 4].map((n) => (
                  <option key={n} value={n}>
                    {n}
                  </option>
                ))}
              </select>
            </label>
          </div>

          <button type="submit" disabled={loading}>
            {loading ? "Generating…" : "Generate"}
          </button>
        </form>

        {error && <div className="error">{error}</div>}
      </aside>

      <main className="panel results-panel">
        {variants.length === 0 && !loading && (
          <div className="empty">
            <p>Fill in the product details and click <strong>Generate</strong>.</p>
          </div>
        )}
        {loading && <div className="empty">Generating content…</div>}
        {variants.map((v, i) => (
          <ResultCard
            key={i}
            index={i}
            total={variants.length}
            data={v}
            onRegenerate={(section) => onRegenerate(i, section)}
          />
        ))}
      </main>
    </div>
  );
}
