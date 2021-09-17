import bs4
import tinycss2
from validators.css_validator import Rules, Rule


def prep_render(html_content: str) -> str:
    soup = bs4.BeautifulSoup(html_content, "html.parser")

    # wrap div around the contents of body
    body = soup.find("body")
    div = soup.new_tag("div", attrs={"id": "solution_rendering"})
    body.wrap(div)
    attrs = body.attrs
    body.unwrap()
    div.wrap(soup.new_tag("body", attrs=attrs))

    # edit the css-rules
    style = soup.find("style")
    # print(style.string)
    rs = Rules(style.string)
    x: Rule
    for x in rs.rules:
        x.selector_str = f"#solution_rendering {x.selector_str}"

    new_style = ""
    for r in rs.rules:
        new_style += f"{r.selector_str}" + "{" + f"{r.name}:{tinycss2.serialize(r.value)}{'!important' if r.important else ''}" + ";}\n   "

    style.string = new_style

    return str(soup.prettify())



html = """
<!DOCTYPE html>
<html>
  <head>
<style>
    body {
        color:red;
    }
    div {
        color: green;
        background_color: green;
    }
</style>
  </head>
  <body>
      AAAAA
  </body>
</html>
"""

#print(prep_render(html))
