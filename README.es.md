# Traductor de markdown gratis

> Advertencia: este artículo está traducido por una máquina, lo que puede dar lugar a una mala calidad o información incorrecta. ¡Lea atentamente!

[![made-with-python](https://img.shields.io/badge/Made%20with-Python-1f425f.svg)](https://www.python.org/)
[![made-with-javascript](https://img.shields.io/badge/Made%20with-JavaScript-1f425f.svg)](https://www.javascript.com)
[![Ask Me Anything !](https://img.shields.io/badge/Ask%20me-anything-1abc9c.svg)](https://GitHub.com/Naereen/ama)

## Breve introducción

El traductor de Markdown gratuito es un documento de marcado de código abierto gratuito (en adelante, denominado traductor MD) basado en la API de traducción de Google, que puede traducir su MD en cualquier tipo de idioma.

Función:

- Traducir MD en cualquier tipo de idioma
- No destruirá el formato original de MD, al tiempo que respalda las reglas de traducción personalizada
- Admite la traducción de múltiples temas y agregue mecanismos de equilibrio de carga al mismo tiempo, lo que puede usar efectivamente las interfaces de traducción de Google y evitar la falla de la traducción de documentos.
- Admite un programa para ejecutar múltiples carpetas y múltiples archivos en una carpeta, lo que aumenta la conveniencia
- Soporte para agregar advertencias a MDS de traducción automática

Referencia de API de traducción de Google [Victorzhang2014/gratis-Google-Traducir: Translación gratuita de Google de la API de traductor de Google (github.com)](https://github.com/VictorZhang2014/free-google-translate) Esta referencia del programa [Cómo usar traduce.google.cn Sitio web gratuito de traducción de Google para traducir todo el documento de Markdown, versión modificada V2 (knightli.com)](https://www.knightli.com/zh-tw/2022/04/24/免費-google-翻譯-整篇-markdown-文檔-修改版/) 

## Instalación y operación

Tenga en cuenta que este programa depende de la traducción de Google, y debe estar conectado a agentes en China continental y otras regiones para usarlo.

### Instalación y uso del programa realizable

El procedimiento ejecutable es utilizado por la configuración predeterminada. La configuración no se puede cambiar. La traducción del chino en más de 10 lenguajes de destino de forma predeterminada es que debido a que mi tiempo y energía son limitados, la configuración no está escrita en el archivo de configuración. Si necesita una configuración personalizada, por favor clonado el código fuente.

1. Descargue la versión de lanzamiento a la derecha
2. Abra la consola del sistema y establezca un agente para la consola
3. Escriba el siguiente comando en la consola

```bash
MarkdownTranslator.exe [-h] folder [folder ...]
```

Coloque la carpeta a traducir para la posición del parámetro, puede agregar varias carpetas. El programa traducirá automáticamente cada carpeta en el archivo especificado en el archivo de configuración en orden.

Por ejemplo, si el idioma de destino especificado es inglés (EN), japonés (JA), entonces `readme.md` El archivo se traducirá a la misma carpeta `readme.en.md` , `readme.ja.md` Luego luego

### Código fuente de clonación y uso

1. Descargue el almacén o descargue el código fuente al área local

```bash
git clone git@github.com:AprilInJuly/Free-Markdown-Translator.git
```

2. Instalar paquete de software `PyExecJS` 

```bash
pip install PyExecJS
```

3. Ingrese el directorio de código, ejecute el código

```bash
python.exe MarkdownTranslator.py [-h] folder [folder ...]
```

Coloque la carpeta a traducir para la posición del parámetro, puede agregar varias carpetas. El programa traducirá automáticamente cada carpeta en el archivo especificado en el archivo de configuración en orden.

Por ejemplo, si el idioma de destino especificado es inglés (EN), japonés (JA), entonces `readme.md` El archivo se traducirá a la misma carpeta `readme.en.md` , `readme.ja.md` Luego luego

## Configuración

por favor en `config.py` Configuración

1.  `insert_warnings` : Controlar si agregar traducción automática delante del artículo
2.  `src_language` : Especifique el idioma de origen, automáticamente indica que Google identifica automáticamente
3.  `warnings_mapping` : Configure el tarón del idioma de destino
4.  `dest_langs` : Configurar el idioma de destino, puede especificar manualmente el idioma de destino, o puede usarlo directamente `warnings_mapping` El idioma de destino en la configuración se traduce en el orden de definición
5.  `skipped_regexs` : Especifique la expresión regular del personaje para omitir la traducción
6.  `detect_filenames` : El nombre del documento MD que debe traducirse en el directorio de archivos
7.  `front_matter_transparent_keys` : La materia frontal de Markdown no necesita traducir piezas
8.  `front_matter_key_value_keys` : La materia frontal debe ser clave-Parte de traducción de formulario de valor
9.  `front_matter_key_value_array_keys` : Asunto frontal-Valor -Rrays Format Translation

### Detalles de configuración del idioma de destino

Debido a que se usa la interfaz de traducción de Google, el idioma de destino debe ser utilizado por ISO 639-1 Código de idioma, puede consultarlo para más detalles [Lista de ISO 639-1 códigos- Wikipedia](https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes) , Aquí hay algún código de idioma de uso común

| Nombre del lenguaje| Este idioma afirma| Código de lenguaje|
| ---------- | ------------------------------ | -------- |
| Chino| Chino, chino, chino| Z h|
| INGLÉS| INGLÉS| Interno|
| japonés| japonés| ja|
| Español| Español| Cepalle|
| ruso| desolado| freno|
| Francés| Fransais| Fría|
| Alemán| Alemán| Delaware|
| Arábica| Desolado| Arkansas|
| hindi| Desolado| Hola|
| portugués| Portugugs| PT|
| coreano| , / Coreano, Corea del Norte 말 / 조선말| KO|


