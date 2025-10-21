---
name: meal-planning
description: Voice-driven family meal planning with pattern-based custody awareness and activity calendar integration. Use when user initiates meal planning conversationally (e.g., "let's plan meals", "help me figure out dinners"). Orchestrates schedule context, leftover management, inventory tracking, meal generation matched to activity complexity, and store-specific shopping list creation to reduce cognitive load and food waste for blended families with repeating custody patterns.
---

# Family Meal Planning & Shopping Orchestration

Voice-driven workflow for meal planning with calendar awareness, leftover intelligence, and shopping list management.

## Prerequisites

- **Mealie MCP server** with pattern-based custody and Home Assistant integration
- MCP server connected via Claude.ai Settings → Integrations with:
  - Mealie API credentials (MEALIE_URL, MEALIE_TOKEN)
  - Home Assistant URL and long-lived access token (HA_URL, HA_TOKEN)
  - Custody pattern configuration (CUSTODY_PATTERN, CUSTODY_CYCLE_START)
- Home Assistant activity calendars: `calendar.benci_boys`, `calendar.boycivengas`
- Mealie shopping list capabilities (implementation via upcoming fork/PR)

## Schedule Context System

### Pattern-Based Custody Schedules

**Approach:** Custody determined by repeating boolean patterns, not calendar events.

**Configuration:**
- `CUSTODY_PATTERN` environment variable (e.g., "2-5-5-2", "2-2-3-2-2-3-blended")
- `CUSTODY_CYCLE_START` anchor date establishes cycle starting point
- Separate patterns for boys and girls support blended families

**Common Patterns:**
- **2-5-5-2**: 2 days home → 5 days away → 5 days home → 2 days away (14-day cycle)
- **2-2-3-2-2-3-blended**: Custom cycle with 3-day together periods (14-day cycle)
- **3-4-4-3**, **week-on-week-off**, **every-other-weekend**: Also supported

**Calculation:** Simple modulo arithmetic determines custody for any date.

### Activity Calendar Integration

**Calendars:** `benci_boys`, `boycivengas` - Home Assistant calendar entities

**Purpose:** Track scheduled activities that impact meal planning complexity.

**Complexity Classification:**
- **CALM** (0 activities): 45-60min recipes OK, elaborate meals welcome
- **MODERATE** (1 activity): 30-45min recipes, one-pot meals
- **BUSY** (2 activities OR 1 late after 6pm): <30min recipes, slow cooker, prep-ahead
- **CHAOTIC** (3+ activities OR 2+ late): Consider takeout or pre-made meals

### Unified Context Tool

Use `get_meal_planning_context_for_period(start_date, end_date)` to get:
- Pattern-based custody status per day (boys HOME/AWAY, girls HOME/AWAY)
- Activity lists from both calendars
- Complexity classification (CALM/MODERATE/BUSY/CHAOTIC)
- Meal planning guidance text

**Single call replaces 2+ calendar queries** and handles all complexity logic.

## Core Workflow

Execute phases sequentially when user initiates meal planning:

### Phase 1: Context Discovery

**Get planning window:**

1. Ask user for planning date range (or default to next 7 days)
2. Call unified meal planning context tool
3. Interpret per-day custody and complexity
4. Provide context-aware response

**Implementation:**

```javascript
// Single call for pattern-based custody + activity context
Mealie:get_meal_planning_context_for_period({
  start_date: "2026-02-06",
  end_date: "2026-02-12",
  timezone: "America/New_York",         // optional
  custody_pattern: "2-5-5-2",           // optional, defaults to env config
  cycle_start: "2026-01-05"             // optional, defaults to env config
})

// Response includes per-day context:
// - custody status (HOME/AWAY for boys and girls)
// - activities list from calendars
// - complexity (CALM, MODERATE, BUSY, CHAOTIC)
// - meal_planning_guidance text
```

**Response pattern:**

```
"I hear ya - looks like a busy week! The [boys/girls] are with you [days], 
and I see [specific activities]. How much shopping are you ready to do now?"
```

**Example using unified context:**

```javascript
// Response from get_meal_planning_context_for_period:
{
  "date_range": {"start": "2026-02-06", "end": "2026-02-12"},
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
        "girls": "AWAY"
      },
      "activities": {
        "benci_boys": [{"summary": "Hockey Practice", "start": "2026-02-06T18:30:00-05:00", ...}],
        "boycivengas": [],
        "count": 1
      },
      "complexity": "MODERATE",
      "meal_planning_guidance": "Boys home, moderate schedule - 30-45min recipes, one-pot meals"
    },
    ...
  ]
}

// Use this to say:
"Got it - boys are with you Thursday and Friday, then away through Tuesday.
Thursday has hockey practice at 6:30, so plan a quick meal before then. Want to
knock out the full week or just through the weekend?"
```

**Clarifications:**
- If no date range provided, ask user to specify duration or specific dates
- Use calendar context to suggest logical planning windows (custody transitions)
- Note time-of-day awareness (Sunday afternoon vs Wednesday night planning)
- Highlight complexity mismatches: "Friday shows 3 activities and girls arriving at 6pm - that's chaos. Suggest takeout or prep-ahead?"

### Phase 2: Leftover Assessment

**Check for leftovers:**

1. Query recent Mealie meal plans (past 3-7 days)
2. Ask user about current leftover situation
3. Identify rehydration opportunities across custody cycles

**Implementation:**

```javascript
// Use Mealie MCP server
Mealie:get_all_mealplans({ 
  start_date: "2024-01-29",  // 7 days ago
  end_date: "2024-02-05"      // today
})
```

**Leftover tracking strategy:**
- When planning meal with leftovers, add note to Mealie meal plan entry: "Leftover from [date] - no ingredients needed"
- Do NOT add ingredients to shopping list for leftover meals
- Track rehydration across custody cycles in memory: "Made spaghetti with girls Monday → reheat for boys Thursday"

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

// Update existing food quantities
Mealie:update_food_quantity({
  food_id: "uuid",
  quantity: "2 lbs",
  units: "2",
  price: "$4.99/lb"
})

// Add new items to inventory
Mealie:add_food_to_inventory({
  name: "Bell peppers",
  household_id: "uuid",
  quantity: "3 peppers",
  units: "3"
})
```

**Inventory tracking workflow:**
- User verbally lists pantry contents
- Claude updates Mealie inventory in real-time using tools above
- Acknowledge each item incrementally for natural conversation flow

**Inventory prioritization:**
- Flag items user mentions are "almost empty" or "expiring soon"
- Prioritize recipes using multiple on-hand items
- Suggest bulk purchases for custody-cycle-friendly items

### Phase 4: Meal Plan Generation

**Match meals to schedule:**

1. Cross-reference planning window with calendar events
2. Categorize each evening by complexity needs:
   - **Calm** (no activities): 45-60min recipes, elaborate meals
   - **Moderate** (single activity): 30-45min recipes, one-pot meals
   - **Busy** (late return, multiple activities): <30min recipes, slow cooker
   - **Chaotic** (overlapping activities, very late): Takeout/on-the-go
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
- Suggest takeout strategically for chaotic nights (prevent burnout)
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
      entry_type: "dinner",
      // Note: Add notes field for leftover tracking when creating leftover meals
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

### Phase 5: Shopping List Creation & Store Assignment

**Build store-specific shopping strategy:**

1. Extract ingredients from all planned meals (exclude leftover meals)
2. De-duplicate against on-hand inventory from Phase 3 (match by food_id)
3. Guide user through ingredient confirmation:
   - Present consolidated ingredient list
   - Ask user which items they already have (double-check inventory)
   - Confirm quantities needed
4. Assign items to stores using baseline distribution
5. **Present breakdown and get user confirmation:**
   - "Here's what I'm thinking: Walmart (15 items - proteins, dairy, basics), Trader Joe's (5 items - specialty sauces, frozen), Wegmans (3 items - organic produce). Sound good or want to adjust?"
6. Create Mealie shopping list(s) based on user-confirmed breakdown

**Store Assignment Baseline (user can override):**
- **Walmart (73%)**: Proteins, dairy, produce (standard), grains, canned goods, frozen basics, bulk items
- **Trader Joe's (20%)**: Unique sauces, specialty cheeses, frozen prepared meals, organic specialty
- **Giant/Wegmans/Weis (7%)**: Store-specific sales, brand preferences, supplemental trips

**Implementation:**

```javascript
// Mealie shopping list tools (available via fork/PR integration)

// Get existing lists
Mealie:get_shopping_lists({ per_page: 20 })

// Create store-specific or unified list
Mealie:create_shopping_list({
  name: "Walmart - Week of Feb 6"
})

// Add items in bulk
Mealie:add_shopping_items_bulk({
  shopping_list_id: "uuid",
  items: [
    {
      note: "Ground beef 2lbs",
      quantity: 2.0,
      unit_id: "lbs-uuid",
      food_id: "beef-uuid"  // Links to inventory for de-duplication
    },
    { note: "Organic marinara sauce" }
  ]
})

// Or leverage recipe integration
Mealie:add_recipe_to_shopping_list({
  shopping_list_id: "uuid",
  recipe_id: "uuid"  // Automatically extracts ingredients
})
```

**Key principles:**
- **User confirmation required** for store assignments - don't assume
- **De-duplication via food_id** - Cross-reference with inventory
- **Flexible organization** - Can create separate lists per store or single unified list with labels
- **Quantity consolidation** - Combine duplicate ingredients across recipes

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
5. Confirm shopping lists created in Mealie

## Response Patterns

**Initiating:**
```
User: "Gotta meal plan Claude"
Claude: "I hear ya - [contextual calendar observation]. How much shopping 
        are you ready to do now?"
```

**Leftovers:**
```
Claude: "Any leftovers we should work with? I see you made [meal] with 
        the [kids] [day]."
User: "Yeah, plus [other leftover]"
Claude: "Great - let's reheat [leftover] [day when appropriate kids home]."
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
- Always call unified meal planning context tool before planning
- Understand pattern-based custody cycles (e.g., "2-5-5-2" = 2 days home, 5 away, 5 home, 2 away)
- Recognize pattern transitions and cycle phases
- Time-of-day awareness in responses (Sunday afternoon planning vs Wednesday night scramble)
- Activity complexity assessment guides meal selection
- Store shopping patterns and user preferences across sessions

**Decision fatigue reduction:**
- Auto-suggest meal complexity based on schedule
- Prioritize recipes using on-hand ingredients
- Proactively address busy nights
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

## References

- **MCP Extension Guide**: See references/mcp-extension-guide.md for complete implementation of Home Assistant calendar tools
- **Shopping intelligence**: See references/shopping-intelligence.md for receipt learning and location-based store assignment
- **Full examples**: See references/examples.md for complete multi-phase planning sessions

## Success Metrics

This skill succeeds when it:
1. Reduces cognitive load - planning feels effortless
2. Eliminates decision fatigue - clear suggestions matched to reality
3. Prevents food waste - uses on-hand items, tracks leftovers
4. Reduces reactive takeout - strategic planning prevents "forgot to shop"
5. Manages budget - awareness of takeout frequency
6. Fits real life - adapts to custody schedules, activities, chaos
7. Saves time - voice workflow faster than manual
8. Increases variety - explores new recipes, avoids repetition