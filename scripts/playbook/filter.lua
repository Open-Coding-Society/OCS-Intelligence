-- Pandoc filter for playbooks (used by scripts/build_playbook.py).
--   * drops the Markdown "# Title" (the cover shows the title from the header)
--   * turns GitHub alerts (> [!NOTE], [!TIP], [!IMPORTANT], [!WARNING], [!CAUTION]) into callouts
--   * rewrites relative links to GitHub URLs, so they still work in the PDF
--   * turns an image on its own line into a figure, captioned with its alt text

local repo_url = "https://github.com/Open-Coding-Society/OCS-Intelligence/blob/main/"
local repo_dir = ""  -- the playbook's folder, relative to the repo root
local seen_title = false

local function normalize(path)
  local parts = {}
  for part in path:gmatch("[^/]+") do
    if part == ".." then
      table.remove(parts)
    elseif part ~= "." then
      table.insert(parts, part)
    end
  end
  return table.concat(parts, "/")
end

local function meta(m)
  if m["repo-dir"] then
    repo_dir = pandoc.utils.stringify(m["repo-dir"])
  end
end

local function header(h)
  if h.level == 1 and not seen_title then
    seen_title = true
    return {}
  end
end

local function link(l)
  local t = l.target
  if t:match("^[%a][%w+.-]*:") or t:match("^#") or t == "" then
    return nil
  end
  l.target = repo_url .. normalize(repo_dir .. "/" .. t)
  return l
end

local labels = { NOTE = "Note", TIP = "Tip", IMPORTANT = "Important", WARNING = "Warning", CAUTION = "Caution" }

local function blockquote(bq)
  local first = bq.content[1]
  if not first or first.t ~= "Para" then
    return nil
  end
  local kind = pandoc.utils.stringify(first.content[1] or ""):match("^%[!(%u+)%]$")
  if not kind or not labels[kind] then
    return nil
  end
  -- drop the marker and the line break after it
  local rest = pandoc.List(first.content)
  rest:remove(1)
  while #rest > 0 and (rest[1].t == "SoftBreak" or rest[1].t == "LineBreak" or rest[1].t == "Space") do
    rest:remove(1)
  end
  local blocks = pandoc.List({ pandoc.Para({ pandoc.Str(labels[kind]) }) })
  blocks[1] = pandoc.Div(blocks[1], { class = "callout-label" })
  if #rest > 0 then
    blocks:insert(pandoc.Para(rest))
  end
  for i = 2, #bq.content do
    blocks:insert(bq.content[i])
  end
  return pandoc.Div(blocks, { class = "callout callout-" .. kind:lower() })
end

local function para(p)
  if #p.content == 1 and p.content[1].t == "Image" then
    local img = p.content[1]
    return pandoc.Figure(pandoc.Plain({ img }), { pandoc.Plain(img.caption) })
  end
end

return {
  { Meta = meta },
  { Header = header, Link = link, BlockQuote = blockquote, Para = para },
}
