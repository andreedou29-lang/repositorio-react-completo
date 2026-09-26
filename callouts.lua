-- Obsidian callouts -> LaTeX tcolorbox. Run with estilos.tex included.
-- Only changes LaTeX output; ordinary block quotes remain unchanged.
local styles = {
  note = {"Nota", "CalloutBlue"},
  info = {"Información", "CalloutBlue"},
  cite = {"Cita", "CalloutGray"},
  quote = {"Cita", "CalloutGray"},
  warning = {"Advertencia", "CalloutAmber"},
  caution = {"Precaución", "CalloutAmber"},
  important = {"Importante", "CalloutPurple"},
  tip = {"Consejo", "CalloutGreen"},
  definition = {"Definición", "CalloutBlue"},
  theorem = {"Teorema", "CalloutPurple"},
  proof = {"Demostración", "CalloutGreen"},
  example = {"Ejemplo", "CalloutGreen"},
}

function BlockQuote(el)
  if not FORMAT:match("latex") then return nil end
  local first = el.content[1]
  if not first or (first.t ~= "Para" and first.t ~= "Plain") then return nil end
  local marker = first.content[1]
  if not marker or marker.t ~= "Str" then return nil end
  local kind, fold, tail = marker.text:match("^%[!([%w_-]+)%]([+-]?)(.*)$")
  if not kind then return nil end
  kind = kind:lower()
  local style = styles[kind] or {kind, "CalloutBlue"}

  -- The first source line is the title. Preserve its inline formatting.
  local title = pandoc.List()
  if tail ~= "" then title:insert(pandoc.Str(tail)) end
  local split = #first.content + 1
  for i = 2, #first.content do
    local item = first.content[i]
    if item.t == "SoftBreak" or item.t == "LineBreak" then
      split = i
      break
    end
    title:insert(item)
  end
  while #title > 0 and title[1].t == "Space" do title:remove(1) end
  while #title > 0 and title[#title].t == "Space" do title:remove(#title) end
  if #title == 0 then title:insert(pandoc.Str(style[1])) end
  local title_tex = pandoc.write(pandoc.Pandoc({pandoc.Plain(title)}), "latex")
  title_tex = title_tex:gsub("%s+$", "")

  local out = pandoc.List({pandoc.RawBlock("latex",
    "\\begin{tcolorbox}[obsidiancallout,colframe=" .. style[2] ..
    ",colback=" .. style[2] .. "!4!white,colbacktitle=" .. style[2] ..
    "!10!white,coltitle=" .. style[2] .. "!65!black,title={" .. title_tex .. "}]")})
  local rest = pandoc.List()
  for i = split + 1, #first.content do rest:insert(first.content[i]) end
  if #rest > 0 then out:insert(pandoc.Para(rest)) end
  for i = 2, #el.content do out:insert(el.content[i]) end
  out:insert(pandoc.RawBlock("latex", "\\end{tcolorbox}"))
  -- [+] and [-] are intentionally expanded in a static PDF.
  return out
end
