import { useEffect, useState } from "react";

export default function ThemeToggle() {
  const [theme, setTheme] = useState(() => localStorage.getItem("theme") || "dark");

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("theme", theme);
  }, [theme]);

  return (
    <button
      onClick={() => setTheme((t) => (t === "dark" ? "light" : "dark"))}
      style={{ display: "flex", alignItems: "center", gap: "6px" }}
    >
      <i className={`ti ${theme === "dark" ? "ti-sun" : "ti-moon"}`} aria-hidden="true" />
      {theme === "dark" ? "Light mode" : "Dark mode"}
    </button>
  );
}