---
name: meal-planning
description: Voice-driven family meal planning that integrates pattern-based custody schedules and activity calendars with Mealie meal planning and shopping lists. Use when the user initiates meal planning conversationally (e.g., "let's plan meals", "gotta meal plan", "help me figure out dinners"). Orchestrates schedule context, leftover management, inventory updates, meal plan generation matched to schedule complexity, and per-store shopping list creation to reduce cognitive load and food waste for busy blended families.
---

# Family Meal Planning & Shopping Orchestration

Voice-driven workflow for meal planning with pattern-based custody awareness, leftover intelligence, and shopping list management.

## Prerequisites

- **Mealie MCP server** with pattern-based custody and Home Assistant integration
- MCP server connected via Claude.ai Settings → Integrations with:
  - Mealie API credentials
  - Home Assistant URL and long-lived access token
  - Custody pattern configuration (e.g., "2-5-5-2")
- Home Assistant activity calendars: `calendar.benci_boys`, `calendar.boycivengas`
- Home Assistant todo lists: `todo.mealie_walmart`, `todo.mealie_trader_joes`, `todo.mealie_giant`, `todo.mealie_wegmans`, `todo.mealie_weis`
- Optional: `calendar.custody_exceptions` for schedule overrides

## Custody Schedule Approach

This skill uses **pattern-based custody schedules** rather than calendar events, dramatically simplifying schedule interpretation:

**Pattern Configuration:**
- Standard custody patterns encoded as boolean arrays (e.g., "2-5-5-2", "3-4-4-3", "week-on-week-off")
- Each pattern defines a repeating cycle (typically 14 days)
- Days when kids are present = True, days away = False
- Anchor date establishes cycle starting point

**Example "2-5-5-2" Pattern:**
```
Cycle: 14 days
| 0| 1| 2| 3| 4| 5| 6| 7| 8| 9|10|11|12|13|
--------------------------------------------
Boys  | X| X|  |  |  |  |  | X| X| X| X| X|  |  |
Girls | X| X|  |  |  |  |  | X| X| X| X| X|  |  |
```

**Exception Handling:**
- Optional `custody_exceptions` calendar overrides pattern for special cases
- Events like "Boys with mom" or "Girls vacation" temporarily modify schedule
- Exceptions are clearly visible and self-documenting

**Benefits:**
- Self-documenting: "We're on 2-5-5-2" is immediately clear
- Simple calculation: day_of_cycle → array lookup → home/away
- Easy validation: Visual pattern shows entire cycle at a glance
- Less maintenance: No recurring calendar events to manage

## Activity Complexity Classification

Activity calendars (`benci_boys`, `boycivengas`) drive meal complexity recommendations:

- **CALM** (0 activities): 45-60min recipes, elaborate meals OK
- **MODERATE** (1 activity): 30-45min recipes, one-pot meals
- **BUSY** (2 activities OR 1 late activity after 6pm): <30min recipes, slow cooker, prep-ahead
- **CHAOTIC** (3+ activities OR 2+ late activities): Consider takeout or pre-made meals

## Core Workflow

Execute phases sequentially when user initiates meal planning:

### Phase 1: Context Discovery

**Get planning window with unified context:**

1. Call unified meal planning context tool for date range
2. Receive per-day custody status (from pattern + exceptions) and activity complexity
3. Provide context-aware response

**Implementation:**

```javascript
// Single call gets everything: pattern-based custody + activity complexity
Mealie:get_meal_planning_context_for_period({ 
  start_date: "2026-02-06",
  end_date: "2026-02-12",
  timezone: "America/New_York",  // optional
  custody_pattern: "2-5-5-2",    // optional, defaults to server config
  cycle_start: "2026-01-05"      // optional, defaults to server config
})
```

**Response structure:**

```javascript
{
  "date_range": {
    "start": "2026-02-06",
    "end": "2026-02-12",
    "timezone": "America/New_York"
  },
  "pattern_info": {
    "name": "2-5-5-2",
    "description": "2 days A, 5 days B, 5 days A, 2 days B",
    "cycle_days": 14,
    "cycle_start": "2026-01-05"
  },
  "combined": [
    {
      "date": "2026-02-06",
      "day_of_week": "Thursday",
      "custody": {
        "boys": "HOME",
        "girls": "AWAY",
        "from_exception": false  // true if exception calendar override applied
      },
      "activities": {
        "benci_boys": [
          {
            "summary": "Hockey Practice",
            "start": "2026-02-06T18:30:00-05:00",
            "end": "2026-02-06T20:00:00-05:00",
            "location": "Ice Rink",
            "description": ""
          }
        ],
        "boycivengas": [],
        "count": 1
      },
      "complexity": "MODERATE",
      "meal_planning_guidance": "Boys home, moderate schedule - 30-45min recipes, one-pot meals"
    },
    // ... more days
  ]
}
```

**Response pattern:**

```
"I hear ya - looks like a busy week! The boys are with you Thursday through 
Sunday, then away until Wednesday. Thursday has hockey at 6:30, so plan a 
quick meal before then. How much shopping are you ready to do now?"
```

**Clarifications:**
- If no date range provided, suggest logical planning windows based on pattern transitions
- Use time-of-day awareness in responses (Sunday afternoon vs Wednesday night planning)
- Highlight complexity mismatches: "Friday shows 3 activities and girls arriving - that's chaos. Suggest takeout or prep-ahead?"

### Phase 2: Leftover Assessment

**Check for leftovers:**

1. Query recent Mealie meal plans (past 3-7 days)
2. Ask user about current leftover situation
3. Identify rehydration opportunities across custody cycles

**Implementation:**

```javascript
// Check what was cooked recently
Mealie:get_all_mealplans({ 
  start_date: "2024-01-29",  // 7 days ago
  end_date: "2024-02-05"      // today
})
```

**Leftover tracking strategy:**
- When planning meal with leftovers, add note to Mealie meal plan entry: "Leftover from [date] - no ingredients needed"
- Do NOT add ingredients to shopping list for leftover meals
- Track rehydration across custody cycles: "Made spaghetti with girls Monday → reheat for boys Thursday"

**Example dialogue:**

```
"Before we dive in - any leftovers right now? I see you made chicken 
stir-fry with the girls last Thursday."
```

### Phase 3: Inventory Update

**Accept voice inventory:**

1. Prompt user to list current pantry/fridge contents
2. Query Mealie foods on-hand for baseline
3. Update Mealie inventory as items are mentioned
4. Acknowledge items incrementally

**Implementation:**

```javascript
// Check current on-hand foods
Mealie:get_foods_on_hand({ search: null })

// Update inventory as user mentions items
Mealie:update_food_quantity({ 
  food_id: "uuid", 
  quantity: "2 lbs", 
  units: "2",
  price: "$4.99/lb"
})

// Or add new items
Mealie:add_food_to_inventory({
  name: "Bell peppers",
  household_id: "uuid",
  quantity: "3 peppers",
  units: "3"
})
```

**Inventory prioritization:**
- Flag items user mentions are "almost empty" or "expiring soon"
- Prioritize recipes using multiple on-hand items
- Suggest bulk purchases for custody-cycle-friendly items

**Example dialogue:**

```
User: "Half gallon milk, two packs spaghetti, ground beef, bell peppers..."
Claude: "Got it - updating inventory. With that spaghetti and beef, we 
        could do quick Bolognese on Tuesday's busy night."
```

### Phase 4: Meal Plan Generation

**Match meals to schedule complexity:**

1. Cross-reference planning window with per-day context from Phase 1
2. Use complexity classification (CALM/MODERATE/BUSY/CHAOTIC) for each day
3. Search Mealie recipes matching complexity and on-hand ingredients
4. Apply 85/15 rule: 85% existing catalog, 15% new recipe exploration
5. Incorporate leftover rehydration from Phase 2
6. Build plan collaboratively, accepting voice modifications
7. Create Mealie meal plan entries in bulk

**Meal complexity matching:**

```javascript
// Search by criteria
Mealie:get_recipes({ 
  search: "quick weeknight",  // or null for browsing
  tags: ["30-minute", "one-pot"],  // as appropriate
  per_page: 5 
})

// Get concise summaries for suggestions
Mealie:get_recipe_concise({ slug: "recipe-slug" })

// Get full recipe when user wants details
Mealie:get_recipe_detailed({ slug: "recipe-slug" })
```

**Takeout management:**
- Suggest takeout strategically for CHAOTIC nights (prevent burnout)
- Track frequency in conversation
- Alert if >3 takeout nights in planning window
- Frame as strategic vs reactive: "This prevents the 'forgot to shop' scramble"

**Create meal plan:**

```javascript
// Bulk create all entries at once
Mealie:create_mealplan_bulk({
  entries: [
    { 
      date: "2024-02-06", 
      recipe_id: "uuid-1", 
      entry_type: "dinner"
    },
    { 
      date: "2024-02-07", 
      title: "Takeout - Pizza night",  // Use title when no recipe
      entry_type: "dinner" 
    },
    // ... more entries
  ]
})
```

### Phase 5: Shopping List Generation

**Build store-specific lists:**

1. Extract ingredients from all planned meals
2. De-duplicate against on-hand inventory from Phase 3
3. Assign items to stores using distribution: Walmart (73%), Trader Joe's (20%), Others (7%)
4. Query existing shopping lists
5. Add new items to appropriate store lists
6. Present summary by store

**Store assignment rules (baseline):**
- **Walmart (primary)**: Proteins, dairy, produce (standard), grains, canned goods, frozen basics, bulk items
- **Trader Joe's (specialty)**: Unique sauces, specialty cheeses, frozen prepared, snacks, organic specialty
- **Giant/Wegmans/Weis (occasional)**: Store-specific sales, brand preferences, supplemental

**Implementation:**

```javascript
// Query existing lists (via Home Assistant MCP)
Home Assistant:todo_get_items({ 
  todo_list: "Mealie Walmart",
  status: "needs_action" 
})

Home Assistant:todo_get_items({ 
  todo_list: "Mealie Trader Joe's",
  status: "needs_action" 
})

// Add items to lists
Home Assistant:HassListAddItem({ 
  name: "Mealie Walmart",
  item: "Ground beef 2lbs" 
})

Home Assistant:HassListAddItem({ 
  name: "Mealie Trader Joe's",
  item: "Organic marinara sauce" 
})
```

**De-duplication:**
- Cross-reference recipe ingredients against Mealie foods on-hand
- Only add items not already in inventory
- Combine quantities for duplicate items across recipes

### Phase 6: Summary & Budget Awareness

**Provide comprehensive summary:**

1. Meal plan summary:
   - Date range and total meals planned
   - Leftover rehydration schedule
   - Takeout count and specific nights
2. Shopping summary:
   - Items per store
   - Estimated trip count
3. Budget check:
   - Takeout frequency for this planning window
   - Alert if >3 nights: "That's busy - we're at X takeout nights. Want to swap one for a quick meal?"
4. Confirm Mealie meal plan entries created
5. Confirm shopping lists updated in Home Assistant

## Response Patterns

**Initiating:**
```
User: "Gotta meal plan Claude"
Claude: "I hear ya - boys are with you Thursday through Sunday according 
        to your 2-5-5-2 pattern. Thursday has hockey at 6:30. How much 
        shopping are you ready to do now?"
```

**Pattern awareness:**
```
Claude: "Looking at your schedule - girls arrive Wednesday noon for their 
        5-day stretch. Want to plan meals they like?"
```

**Leftovers:**
```
Claude: "Any leftovers we should work with? I see you made chicken stir-fry 
        with the girls last Thursday."
User: "Yeah, plus some pasta"
Claude: "Great - let's reheat the stir-fry when boys get home Friday."
```

**Inventory:**
```
User: "Half gallon milk, two packs spaghetti, ground beef, bell peppers..."
Claude: "Got it - updating inventory. With that spaghetti and beef, we 
        could do quick Bolognese on Tuesday's busy night."
```

**Schedule-aware:**
```
Claude: "Looking at Wednesday - both kids have activities until 7:30pm. 
        Suggest either slow cooker (prep morning) or takeout. Thoughts?"
```

**Exception handling:**
```
Claude: "I see an exception on your calendar - 'Boys with mom' this Friday. 
        So just planning for girls that night?"
```

**Budget awareness:**
```
Claude: "Heads up - we've suggested takeout 4 nights this week. That's 
        more than usual. Want to swap one for a 20-minute option?"
```

## Key Principles

**Voice-first design:**
- Accept natural language input
- Confirm understanding incrementally
- Keep responses concise
- Ask clarifying questions only when needed
- Summarize complex operations clearly

**Context awareness:**
- Always query unified context before planning
- Understand custody patterns (e.g., "2-5-5-2" means 2 days, 5 days away, 5 days home, 2 days away)
- Recognize pattern transitions and cycle phases
- Note exceptions from custody_exceptions calendar
- Time-of-day awareness in responses
- Activity complexity assessment

**Decision fatigue reduction:**
- Auto-suggest meal complexity based on activity schedule
- Prioritize recipes using on-hand ingredients
- Proactively address BUSY and CHAOTIC nights
- Limit decision points
- Default to proven patterns (85/15 rule)

**Food waste prevention:**
- De-duplicate shopping lists against inventory
- Prioritize recipes using existing ingredients
- Plan leftover rehydration across custody cycles
- Flag expiring items for immediate use

**Budget management:**
- Track takeout frequency
- Alert when exceeding threshold (>3/week)
- Frame takeout as strategic vs reactive
- No judgment, just awareness

## Pattern Configuration

The MCP server is configured with a custody pattern that defines the repeating schedule. Common patterns include:

**Standard Patterns:**
- **2-5-5-2**: 2 days home, 5 days away, 5 days home, 2 days away (14-day cycle)
- **3-4-4-3**: 3 days home, 4 days away, 4 days home, 3 days away (14-day cycle)
- **2-2-3**: 2 days home, 2 days away, 3 days home (7-day cycle, repeats weekly)
- **Week-on-week-off**: Alternating full weeks (14-day cycle)
- **Every-other-weekend**: Weekdays with one parent, alternating weekends (14-day cycle)

**Blended families** can have different patterns for different groups of children.

**Pattern visualization** (example "2-5-5-2"):
```
| 0| 1| 2| 3| 4| 5| 6| 7| 8| 9|10|11|12|13|
--------------------------------------------
Boys  | X| X|  |  |  |  |  | X| X| X| X| X|  |  |
Girls | X| X|  |  |  |  |  | X| X| X| X| X|  |  |
```

X = present (HOME), blank = away (AWAY)

## Exception Calendar

When custody deviates from the pattern (swaps, vacations, makeup weekends), events are added to the `custody_exceptions` calendar:

**Event naming:**
- Include "boys" or "girls" to specify which group
- Include "away"/"mom"/"vacation" for away overrides
- Include "home"/"dad"/"makeup" for home overrides

**Examples:**
- "Boys with mom" → Boys marked AWAY for event duration
- "Girls vacation with dad" → Girls marked AWAY for event duration  
- "Boys makeup weekend" → Boys marked HOME for event duration

The unified context tool automatically detects and applies these exceptions, flagging days with `"from_exception": true` in the response.

## Success Metrics

This skill succeeds when it:
1. Reduces cognitive load - planning feels effortless
2. Eliminates decision fatigue - clear suggestions matched to reality
3. Prevents food waste - uses on-hand items, tracks leftovers
4. Reduces reactive takeout - strategic planning prevents "forgot to shop"
5. Manages budget - awareness of takeout frequency
6. Fits real life - adapts to custody patterns, activities, chaos
7. Saves time - voice workflow faster than manual
8. Increases variety - explores new recipes, avoids repetition
9. Provides clarity - pattern-based schedule is self-documenting
10. Reduces errors - simple pattern lookup vs complex event parsing