{#
    The document shell generated pages extend.

    This is deliberately bare: a valid HTML document, a title and a content
    slot, and nothing else. No stylesheet, no navigation, no footer, no
    framework classes. It exists so that what `make:auth` and `make:admin`
    generate actually renders, not to be a theme.

    It is yours from the moment it is written. Add your own markup, your own
    stylesheet and your own navigation here; nothing in the engine reads this
    file or depends on its contents beyond the two sections below.

    Sections:
      title    the document title
      content  the page body
#}
<!DOCTYPE html>
<html lang="{{ locale() }}">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>@yield("title")</title>
</head>
<body>
@yield("content")
</body>
</html>
