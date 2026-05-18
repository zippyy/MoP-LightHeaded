--[[
LightHeaded Midnight compatibility layer

This file intentionally keeps the original LightHeaded code mostly intact and
fills in the legacy WoW API names that the 5.4.8-era addon expects. The goal is
not a full modern rewrite; it is a first-pass compatibility bridge so the addon
can load on modern clients and continue using its embedded quest data.
]]

local ADDON_NAME = ...

-- Retail moved addon APIs under C_AddOns. Keep the old globals available for
-- the legacy code and the embedded Dongle library.
if C_AddOns then
    GetAddOnMetadata = GetAddOnMetadata or C_AddOns.GetAddOnMetadata
    LoadAddOn = LoadAddOn or C_AddOns.LoadAddOn
    IsAddOnLoaded = IsAddOnLoaded or C_AddOns.IsAddOnLoaded
    EnableAddOn = EnableAddOn or C_AddOns.EnableAddOn
    DisableAddOn = DisableAddOn or C_AddOns.DisableAddOn
end

-- Lua 5.1 compatibility helpers that older addons still assume exist.
unpack = unpack or table.unpack
getfenv = getfenv or function(level)
    if level == 0 then
        return _G
    end
    local info = debug and debug.getinfo and debug.getinfo((level or 1) + 1, "f")
    if info and info.func and debug.getupvalue then
        local i = 1
        while true do
            local name, value = debug.getupvalue(info.func, i)
            if name == "_ENV" then
                return value
            elseif not name then
                break
            end
            i = i + 1
        end
    end
    return _G
end

-- TEXT() was commonly used by old FrameXML code.
TEXT = TEXT or function(text) return text end
OKAY = OKAY or OK

-- The old quest log was removed/reworked. Point the old global frame names at
-- the closest modern quest UI frames so frame parenting does not explode.
local function GetQuestParentFrame()
    return QuestMapFrame or QuestLogPopupDetailFrame or QuestFrame or UIParent
end

QuestLogFrame = QuestLogFrame or GetQuestParentFrame()
QuestLogDetailFrame = QuestLogDetailFrame or QuestLogPopupDetailFrame or QuestFrame or QuestLogFrame
QuestNPCModel = QuestNPCModel or QuestModelScene or QuestFrame and QuestFrame.ModelScene

-- Modern quest selection/link helpers.
local function GetSelectedQuestID()
    if C_QuestLog then
        if C_QuestLog.GetSelectedQuest then
            local questID = C_QuestLog.GetSelectedQuest()
            if questID and questID ~= 0 then
                return questID
            end
        end
    end

    if QuestMapFrame and QuestMapFrame.DetailsFrame and QuestMapFrame.DetailsFrame.questID then
        return QuestMapFrame.DetailsFrame.questID
    end

    if QuestLogPopupDetailFrame and QuestLogPopupDetailFrame.questID then
        return QuestLogPopupDetailFrame.questID
    end
end

GetQuestLogSelection = GetQuestLogSelection or function()
    local questID = GetSelectedQuestID()
    if C_QuestLog and C_QuestLog.GetLogIndexForQuestID and questID then
        return C_QuestLog.GetLogIndexForQuestID(questID)
    end
    return questID
end

GetQuestLink = GetQuestLink or function(index)
    local questID = nil

    if C_QuestLog then
        if type(index) == "number" and C_QuestLog.GetInfo then
            local info = C_QuestLog.GetInfo(index)
            questID = info and info.questID
        end

        questID = questID or GetSelectedQuestID()

        if questID and C_QuestLog.GetQuestLink then
            local link = C_QuestLog.GetQuestLink(questID)
            if link then
                return link
            end
        end
    end

    if questID then
        local title = C_QuestLog and C_QuestLog.GetTitleForQuestID and C_QuestLog.GetTitleForQuestID(questID) or tostring(questID)
        return ("|cffffff00|Hquest:%d:0|h[%s]|h|r"):format(questID, title)
    end
end

SelectQuestLogEntry = SelectQuestLogEntry or function(index)
    if C_QuestLog and C_QuestLog.SetSelectedQuest then
        local questID = index
        if type(index) == "number" and C_QuestLog.GetInfo then
            local info = C_QuestLog.GetInfo(index)
            questID = info and info.questID or index
        end
        if questID then
            C_QuestLog.SetSelectedQuest(questID)
        end
    end
end

QuestLogTitleButton_OnClick = QuestLogTitleButton_OnClick or function() end
WatchFrameLinkButtonTemplate_OnClick = WatchFrameLinkButtonTemplate_OnClick or function() end

-- Old world map APIs used by LightHeaded's waypoint conversions. These are
-- best-effort shims; modern waypoint addons should use questID based routing.
GetMapNameByID = GetMapNameByID or function(mapID)
    local info = C_Map and C_Map.GetMapInfo and C_Map.GetMapInfo(mapID)
    return info and info.name
end

GetMapContinents = GetMapContinents or function()
    if not C_Map or not C_Map.GetMapChildrenInfo then return end
    local children = C_Map.GetMapChildrenInfo(946, Enum.UIMapType.Continent, true) or {}
    local names = {}
    for _, info in ipairs(children) do
        table.insert(names, info.name)
    end
    return unpack(names)
end

GetMapZones = GetMapZones or function(continentIndex)
    if not C_Map or not C_Map.GetMapChildrenInfo then return end
    local continents = C_Map.GetMapChildrenInfo(946, Enum.UIMapType.Continent, true) or {}
    local continent = continents[continentIndex]
    if not continent then return end
    local zones = C_Map.GetMapChildrenInfo(continent.mapID, Enum.UIMapType.Zone, true) or {}
    local names = {}
    for _, info in ipairs(zones) do
        table.insert(names, info.name)
    end
    return unpack(names)
end

GetCurrentMapContinent = GetCurrentMapContinent or function() return nil end
GetCurrentMapZone = GetCurrentMapZone or function() return nil end

-- Interface options were replaced by Settings. Keep the slash command from
-- erroring even if the modern settings panel is not registered yet.
InterfaceOptionsFrame_OpenToCategory = InterfaceOptionsFrame_OpenToCategory or function(category)
    if Settings and Settings.OpenToCategory then
        pcall(Settings.OpenToCategory, category)
    end
end

-- Chat edit box changed names over time.
ChatFrameEditBox = ChatFrameEditBox or DEFAULT_CHAT_FRAME and DEFAULT_CHAT_FRAME.editBox

-- Do not patch global widget metatables here. Global frame metatable patches
-- taint unrelated Blizzard UI paths, especially nameplates/health bars in
-- Midnight. Any object API compatibility has to be handled inside LightHeaded
-- code itself.

-- Keep diagnostics simple in-game.
_G.LightHeaded_MidnightCompat = true
