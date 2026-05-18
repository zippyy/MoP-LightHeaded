local ADDON_NAME = ...
local LH = _G.LightHeaded or {}
_G.LightHeaded = LH

local frame
local pages = {}
local page = 1
local currentQID
local currentURL

local function msg(text)
    DEFAULT_CHAT_FRAME:AddMessage("|cff33ff99LightHeaded:|r " .. tostring(text))
end

local function loadAddon(name)
    if C_AddOns and C_AddOns.LoadAddOn then
        return C_AddOns.LoadAddOn(name)
    elseif LoadAddOn then
        return LoadAddOn(name)
    end
end

local function loadNames()
    if not LH_QIDNames then
        loadAddon("LightHeaded_Data_QIDNames")
    end
    return LH_QIDNames
end

local function questName(qid)
    local names = loadNames()
    if not names then return tostring(qid) end
    local pat = string.format("\031%s\031[^\030]*\030([^\030]*)\030", tostring(qid))
    return names:match(pat) or tostring(qid)
end

local function questData(qid)
    if not LH_QIDMap then return end
    for i = #LH_QIDMap, 1, -1 do
        if qid >= LH_QIDMap[i] then
            local varname = LH_QIDMap.vars and LH_QIDMap.vars[i]
            local addon = LH_QIDMap.addons and LH_QIDMap.addons[i]
            if varname and not _G[varname] and addon then
                loadAddon(addon)
            end
            return varname and _G[varname] and _G[varname][qid]
        end
    end
end

local function escapePattern(text)
    return tostring(text or ""):gsub("([%%%^%$%(%)%.%[%]%*%+%-%?])", "%%%1")
end

local qinfoPattern = "([^\031]*)\031([^\031]*)\031([^\031]*)\031([^\031]*)\031([^\031]*)\031([^\031]*)\031([^\031]*)\031([^\031]*)\031([^\031]*)\031([^\031]*)\031([^\031]*)\031([^\031]*)\031([^\030]-)\030"
local commentPattern = string.rep("([^\031]*)\031", 6) .. "$"

local function clean(text)
    text = text or ""
    text = text:gsub("%[/?[biusmall]+%]", "")
    text = text:gsub("%[quote%](.-)%[/quote%]", "\n> %1\n")
    text = text:gsub("%[url=([^%]]-)%](.-)%[/url%]", "%2")
    text = text:gsub("%[li%](.-)%[/li%]", " - %1\n")
    text = text:gsub("%[/?[ou]l%]", "")
    return text
end

local function selectedQuestID()
    if C_QuestLog and C_QuestLog.GetSelectedQuest then
        local qid = C_QuestLog.GetSelectedQuest()
        if qid and qid ~= 0 then return qid end
    end
    if QuestMapFrame and QuestMapFrame.DetailsFrame then
        return QuestMapFrame.DetailsFrame.questID
    end
end

local function showURLBox(url)
    StaticPopupDialogs.LIGHTHEADED_URL = StaticPopupDialogs.LIGHTHEADED_URL or {
        text = "Copy this Wowhead URL",
        button1 = CLOSE,
        hasEditBox = true,
        editBoxWidth = 420,
        timeout = 0,
        whileDead = true,
        hideOnEscape = true,
        OnShow = function(self)
            local editBox = self.editBox or _G[self:GetName() .. "EditBox"]
            if editBox then
                editBox:SetText(currentURL or "")
                editBox:SetFocus()
                editBox:HighlightText()
            end
        end,
        EditBoxOnEscapePressed = function(self) self:GetParent():Hide() end,
    }
    currentURL = url
    StaticPopup_Show("LIGHTHEADED_URL")
end

local function fallbackPage(qid)
    local title = C_QuestLog and C_QuestLog.GetTitleForQuestID and C_QuestLog.GetTitleForQuestID(qid) or questName(qid)
    local url = "https://www.wowhead.com/quest=" .. tostring(qid)
    currentURL = url
    return table.concat({
        "|cffffd100" .. tostring(title or qid) .. "|r",
        "Quest ID: " .. tostring(qid),
        "",
        "No embedded LightHeaded data exists for this quest yet.",
        "",
        "This is expected for Midnight/new retail quests because the bundled LightHeaded data is from the old MoP-era database.",
        "",
        "Wowhead:",
        url,
        "",
        "Click the Wowhead button below to copy the URL.",
        "",
        "For true in-game comments, generate a new data pack and add it as LightHeaded_Data_Midnight. WoW addons cannot fetch live web pages directly while the game is running."
    }, "\n")
end

local function render()
    if not frame then return end
    frame.body:SetText(pages[page] or "No data.")
    frame.pager:SetText("Page " .. tostring(page) .. " / " .. tostring(#pages))
    frame.prev:SetEnabled(page > 1)
    frame.next:SetEnabled(page < #pages)
    frame.wowhead:SetEnabled(currentURL ~= nil)
end

local function build(qid)
    wipe(pages)
    qid = tonumber(qid)
    currentQID = qid
    currentURL = qid and ("https://www.wowhead.com/quest=" .. tostring(qid)) or nil

    if not qid then
        pages[1] = "No quest selected. Use /lh <questID> or select a quest first."
        return
    end

    local data = questData(qid)
    if not data then
        pages[1] = fallbackPage(qid)
        return
    end

    local title = questName(qid)
    local _, sharable, level, reqlev, stype, sname, sid, etype, ename, eid, exp = data[1]:match(qinfoPattern)
    local info = {"|cffffd100" .. title .. "|r", "Quest ID: " .. qid}
    if level and level ~= "" then table.insert(info, "Level: " .. level) end
    if reqlev and reqlev ~= "" then table.insert(info, "Required Level: " .. reqlev) end
    if sname and sname ~= "" then table.insert(info, "Starts: " .. sname) end
    if ename and ename ~= "" then table.insert(info, "Ends: " .. ename) end
    if exp and exp ~= "" then table.insert(info, "Experience: " .. exp) end
    table.insert(info, "")
    table.insert(info, "Wowhead: " .. currentURL)
    pages[1] = table.concat(info, "\n")

    for i = 2, #data do
        local user, _, rating, _, date, body = data[i]:match(commentPattern)
        local head = "|cffffd100Comment " .. (i - 1) .. "|r"
        if user and user ~= "" then head = head .. " by " .. user end
        if date and date ~= "" then head = head .. " on " .. date end
        table.insert(pages, head .. "\n\n" .. clean(body))
    end
end

local function search(query)
    wipe(pages)
    query = tostring(query or ""):match("^%s*(.-)%s*$")
    if query == "" then
        pages[1] = "Search is empty. Use /lh <questID> or /lh <quest name>."
        return
    end

    local names = loadNames()
    if not names then
        pages[1] = "Quest name data is unavailable. Try /lh <questID>."
        return
    end

    local lower = names:lower()
    local result = {}
    local pattern = string.format("(\031[^\030]+)\030([^\030]-%s[^\030]-)\030", escapePattern(query:lower()))
    for qidList in lower:gmatch(pattern) do
        for qid in qidList:gmatch("\031(%d+)") do
            table.insert(result, qid .. " - " .. questName(qid))
            if #result >= 50 then break end
        end
        if #result >= 50 then break end
    end

    if #result == 0 then
        pages[1] = "No embedded quest-name matches for: " .. query .. "\n\nTry /lh <questID>. New Midnight quests will need a generated data pack."
    else
        pages[1] = "Search results for: " .. query .. "\n\n" .. table.concat(result, "\n") .. "\n\nOpen one with /lh <questID>."
    end
    currentURL = "https://www.wowhead.com/search?q=" .. query:gsub(" ", "+")
end

local function createUI()
    if frame then return end
    frame = CreateFrame("Frame", "LightHeadedMidnightFrame", UIParent, "BackdropTemplate")
    frame:SetSize(560, 460)
    frame:SetPoint("CENTER")
    frame:SetFrameStrata("DIALOG")
    frame:EnableMouse(true)
    frame:SetMovable(true)
    frame:RegisterForDrag("LeftButton")
    frame:SetScript("OnDragStart", frame.StartMoving)
    frame:SetScript("OnDragStop", frame.StopMovingOrSizing)
    frame:SetBackdrop({bgFile="Interface\\DialogFrame\\UI-DialogBox-Background", edgeFile="Interface\\DialogFrame\\UI-DialogBox-Border", tile=true, tileSize=32, edgeSize=32, insets={left=8,right=8,top=8,bottom=8}})

    frame.title = frame:CreateFontString(nil, "ARTWORK", "GameFontNormalLarge")
    frame.title:SetPoint("TOPLEFT", 18, -16)
    frame.title:SetText("LightHeaded Midnight")

    local close = CreateFrame("Button", nil, frame, "UIPanelCloseButton")
    close:SetPoint("TOPRIGHT", -5, -5)

    local scroll = CreateFrame("ScrollFrame", nil, frame, "UIPanelScrollFrameTemplate")
    scroll:SetPoint("TOPLEFT", 22, -52)
    scroll:SetPoint("BOTTOMRIGHT", -36, 82)
    local child = CreateFrame("Frame", nil, scroll)
    child:SetSize(480, 1)
    scroll:SetScrollChild(child)
    frame.body = child:CreateFontString(nil, "ARTWORK", "GameFontHighlight")
    frame.body:SetPoint("TOPLEFT")
    frame.body:SetWidth(470)
    frame.body:SetJustifyH("LEFT")
    frame.body:SetJustifyV("TOP")

    frame.pager = frame:CreateFontString(nil, "ARTWORK", "GameFontNormal")
    frame.pager:SetPoint("BOTTOM", 0, 53)

    frame.prev = CreateFrame("Button", nil, frame, "UIPanelButtonTemplate")
    frame.prev:SetSize(90, 24)
    frame.prev:SetText("Previous")
    frame.prev:SetPoint("BOTTOMLEFT", 22, 46)
    frame.prev:SetScript("OnClick", function() if page > 1 then page = page - 1; render() end end)

    frame.next = CreateFrame("Button", nil, frame, "UIPanelButtonTemplate")
    frame.next:SetSize(90, 24)
    frame.next:SetText("Next")
    frame.next:SetPoint("BOTTOMRIGHT", -22, 46)
    frame.next:SetScript("OnClick", function() if page < #pages then page = page + 1; render() end end)

    frame.wowhead = CreateFrame("Button", nil, frame, "UIPanelButtonTemplate")
    frame.wowhead:SetSize(130, 24)
    frame.wowhead:SetText("Copy Wowhead URL")
    frame.wowhead:SetPoint("BOTTOM", 0, 18)
    frame.wowhead:SetScript("OnClick", function() if currentURL then showURLBox(currentURL) end end)
    frame:Hide()
end

local function show(qid)
    createUI()
    build(qid or selectedQuestID())
    page = 1
    render()
    frame:Show()
end

local function showSearch(query)
    createUI()
    search(query)
    page = 1
    render()
    frame:Show()
end

LH.ShowQuest = show
LH.Search = showSearch
LH.OpenWowhead = function(qid) showURLBox("https://www.wowhead.com/quest=" .. tostring(qid or currentQID or selectedQuestID() or "")) end

SLASH_LIGHTHEADED1 = "/lh"
SLASH_LIGHTHEADED2 = "/lightheaded"
SLASH_LIGHTHEADED3 = "/lighthead"
SlashCmdList.LIGHTHEADED = function(input)
    input = input and input:match("^%s*(.-)%s*$") or ""
    if input == "" then
        show(selectedQuestID())
        return
    end
    if input == "wowhead" or input == "url" then
        LH.OpenWowhead()
        return
    end
    local qid = tonumber(input)
    if qid then
        show(qid)
    else
        showSearch(input)
    end
end

msg("Midnight-safe runtime loaded. Use /lh, /lh <questID>, /lh <search>, or /lh wowhead.")
