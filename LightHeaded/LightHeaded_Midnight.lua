local ADDON_NAME = ...
local LH = _G.LightHeaded or {}
_G.LightHeaded = LH

local frame
local pages = {}
local page = 1

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

local function render()
    if not frame then return end
    frame.body:SetText(pages[page] or "No data.")
    frame.pager:SetText("Page " .. tostring(page) .. " / " .. tostring(#pages))
    frame.prev:SetEnabled(page > 1)
    frame.next:SetEnabled(page < #pages)
end

local function build(qid)
    wipe(pages)
    qid = tonumber(qid)
    if not qid then
        pages[1] = "No quest selected. Use /lh <questID>."
        return
    end

    local data = questData(qid)
    if not data then
        pages[1] = "No LightHeaded data found for quest ID " .. qid .. "."
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
    pages[1] = table.concat(info, "\n")

    for i = 2, #data do
        local user, _, rating, _, date, body = data[i]:match(commentPattern)
        local head = "|cffffd100Comment " .. (i - 1) .. "|r"
        if user and user ~= "" then head = head .. " by " .. user end
        if date and date ~= "" then head = head .. " on " .. date end
        table.insert(pages, head .. "\n\n" .. clean(body))
    end
end

local function createUI()
    if frame then return end
    frame = CreateFrame("Frame", "LightHeadedMidnightFrame", UIParent, "BackdropTemplate")
    frame:SetSize(520, 440)
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
    scroll:SetPoint("BOTTOMRIGHT", -36, 58)
    local child = CreateFrame("Frame", nil, scroll)
    child:SetSize(440, 1)
    scroll:SetScrollChild(child)
    frame.body = child:CreateFontString(nil, "ARTWORK", "GameFontHighlight")
    frame.body:SetPoint("TOPLEFT")
    frame.body:SetWidth(430)
    frame.body:SetJustifyH("LEFT")
    frame.body:SetJustifyV("TOP")

    frame.pager = frame:CreateFontString(nil, "ARTWORK", "GameFontNormal")
    frame.pager:SetPoint("BOTTOM", 0, 25)

    frame.prev = CreateFrame("Button", nil, frame, "UIPanelButtonTemplate")
    frame.prev:SetSize(90, 24)
    frame.prev:SetText("Previous")
    frame.prev:SetPoint("BOTTOMLEFT", 22, 18)
    frame.prev:SetScript("OnClick", function() if page > 1 then page = page - 1; render() end end)

    frame.next = CreateFrame("Button", nil, frame, "UIPanelButtonTemplate")
    frame.next:SetSize(90, 24)
    frame.next:SetText("Next")
    frame.next:SetPoint("BOTTOMRIGHT", -22, 18)
    frame.next:SetScript("OnClick", function() if page < #pages then page = page + 1; render() end end)
    frame:Hide()
end

local function show(qid)
    createUI()
    build(qid or selectedQuestID())
    page = 1
    render()
    frame:Show()
end

LH.ShowQuest = show

SLASH_LIGHTHEADED1 = "/lh"
SLASH_LIGHTHEADED2 = "/lightheaded"
SLASH_LIGHTHEADED3 = "/lighthead"
SlashCmdList.LIGHTHEADED = function(input)
    input = input and input:match("^%s*(.-)%s*$") or ""
    show(tonumber(input) or selectedQuestID())
end

msg("Midnight-safe runtime loaded. Use /lh <questID>.")
