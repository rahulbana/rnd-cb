import { useState } from "react";

export default function SearchForm({ onSubmit, loading }) {
  const [title, setTitle] = useState("");
  const [author, setAuthor] = useState("");

  function handleSubmit(e) {
    e.preventDefault();
    if (!title.trim()) return;
    onSubmit({ title: title.trim(), author: author.trim() });
  }

  return (
    <form className="search-form" onSubmit={handleSubmit}>
      <div className="field">
        <label htmlFor="title">Book title</label>
        <input
          id="title"
          type="text"
          placeholder="e.g. The Great Gatsby"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          disabled={loading}
          autoFocus
        />
      </div>
      <div className="field">
        <label htmlFor="author">Author (optional)</label>
        <input
          id="author"
          type="text"
          placeholder="e.g. F. Scott Fitzgerald"
          value={author}
          onChange={(e) => setAuthor(e.target.value)}
          disabled={loading}
        />
      </div>
      <button type="submit" className="primary" disabled={loading || !title.trim()}>
        {loading ? "Researching…" : "Analyze book"}
      </button>
    </form>
  );
}
