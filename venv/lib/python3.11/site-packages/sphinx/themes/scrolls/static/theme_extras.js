const initialiseThemeExtras = () => {
  const toc = document.getElementById("toc")
  toc.style.display = ""
  const items = toc.getElementsByTagName("ul")[0]
  items.style.display = "none"
    toc.getElementsByTagName("h3").addEventListener("click", () => {
      if (items.style.display !== "none") toc.classList.remove("expandedtoc")
      else toc.classList.add("expandedtoc");
    })
}
if (document.readyState !== "loading") initialiseThemeExtras()
else document.addEventListener("DOMContentLoaded", initialiseThemeExtras)
