# Contributing SVG Icons

This project uses icons from Font Awesome Free (https://fontawesome.com), version 6.7.2.  
To ensure visual consistency, traceability, and proper license attribution, follow these guidelines when adding or modifying icons.

---

## ⚠️ Important: Changing Font Awesome Version

If you update to a different Font Awesome version, **you must update all SVG files** and comments to reflect the new version number and licensing URL accordingly.

Example (update both the SVG files and documentation):

From:
```xml
<!--!Font Awesome Free 6.7.2 by @fontawesome - https://fontawesome.com License - https://fontawesome.com/license/free Copyright 2025 Fonticons, Inc.-->
```
To (example):
```xml
<!--!Font Awesome Free X.Y.Z by @fontawesome - https://fontawesome.com License - https://fontawesome.com/license/free Copyright YYYY Fonticons, Inc.-->
```
---

## Adding a New Icon

1. Use only icons from Font Awesome Free (v6.7.2).
2. Save the icon as a .svg file in this directory.
3. Include the following attribution comment at the top of the file (do not alter it):
```xml
<!--!Font Awesome Free 6.7.2 by @fontawesome - https://fontawesome.com License - https://fontawesome.com/license/free Copyright 2025 Fonticons, Inc.-->
```
4. Above the `<path>` element, add the following metadata comment, filling in the correct values:
```xml
<!-- 
  Icon Name: [icon-name]
  Icon Family: [classic | sharp | brands | etc.]
  Icon Style: [solid | regular | light | thin | duotone | etc.]
-->
```
---

## Example SVG Structure

```xml
<svg width="..." height="..." viewBox="..." xmlns="http://www.w3.org/2000/svg">
  <!--!Font Awesome Free 6.7.2 by @fontawesome - https://fontawesome.com License - https://fontawesome.com/license/free Copyright 2025 Fonticons, Inc.-->
  <!-- 
    Icon Name: [icon-name]
    Icon Family: [icon-family]
    Icon Style: [icon-style]
  -->
  <defs>
    <g id="icon">
      <path d="..."/>
    </g>
  </defs>
  <use xlink:href="#icon" x="0" y="0" fill="#000000"/>
</svg>
