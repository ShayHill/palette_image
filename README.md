# palette_image

Genere imágenes para mi artículo sobre paletas en [shayallenhill.com/ai-generated-palettes](https://shayallenhill.com/ai-generated-palettes/).

Cada una de las imàgenes contiene un cadena de commentario JSON con la siguiente estructura:

```json
{
  "filename": "pencils.jpg",
  "colors": ["#191919", "#000000", "#ff0000", "#00ff00", "#0000ff", "#ffff00"],
  "ratios": [1, 1, 1, 1, 1, 1],
  "center": null,
  "colornames": ["Thamar Black", "Black", "Red", "Green", "Blue", "Yellow"],
  "comment": "Pencils"
}
```

... cuál debería ser suficiente información para crear la paleta en otro formato o crear una descripción de texto acompañante.

