---
name: dax_query
description: Execute DAX queries on Power BI datasets. Use this skill to query BIM data, analyze datasets, retrieve filtered datasets, and get summarized metrics. Returns results in JSON format.
version: 1.0.0
author: BIM Framework
category: data_query
tags: [bim, powerbi, dax, query, data, analysis, schema, tables, columns]
---

# DAX Query Skill

A comprehensive skill for executing DAX queries on Power BI data. This skill enables you to query BIM data, analyze datasets, retrieve filtered datasets, get summarized metrics, and return formatted results.

---

## Description

The DAX Query Skill executes DAX queries on Power BI datasets and returns formatted results. It supports:

- **Data Query**: Execute any DAX query to retrieve data
- **Data Analysis**: Aggregate, filter, and analyze BIM data
- **Filtered Results**: Apply filters to get specific data subsets
- **Summarized Metrics**: Get counts, sums, averages, and other aggregations

---

## When to Use This Skill

**✅ YES, use DAX query when:**
- User asks for specific data from tables
- User asks for aggregations (sum, count, average, min, max)
- User asks for filtered data
- User asks for metrics or statistics
- User asks to "show", "list", "get", "display" data
- User asks "how many", "what is the total", "what is the average"

**❌ NO, don't use DAX query when:**
- User is asking a general question not about data
- User is asking for help or about capabilities
- User is asking about the system itself

---

## How to Use This Skill

1. **Understand the User's Question**: Determine what data is needed
2. **Select the Appropriate DAX Pattern**: Use the patterns below
3. **Generate the DAX Query**: Create a valid DAX query
4. **Include in Response**: Place the DAX query in `skill_parameters.dax_query`

**IMPORTANT**: The `dax_query` skill MUST include a DAX Query in the `skill_parameters`. The DAX Query must be a valid DAX query that can be executed on the Power BI dataset.

---

## 🔴 CRITICAL: Scalar Values Must Use Curly Braces {}

When using scalar functions like `COUNTROWS`, `SUM`, `AVERAGE`, `MIN`, `MAX` directly with `EVALUATE`, you MUST wrap them in **curly braces `{}`** to create a table.

### ❌ WRONG (Will cause error):
```
dax
EVALUATE
COUNTROWS('Assets')
```

### ✅ CORRECT (Will work):
```
dax
EVALUATE
{ COUNTROWS('Assets') }
```

---


## Common DAX Patterns

Get all data from a table:
```
dax 
Evaluate 'TableName'
```

Filtered data:
```
dax 
Evaluate FILTER('TableName', 'TableName'[Column] = "Value")
```

Select specific columns:
```
dax
Evaluate SELECTCOLUMNS('TableName', "Column1", [Column1], "Column2", [Column2])
```

Count rows:
```
dax
EVALUATE ROW("Count", COUNTROWS('TableName'))
```

Sum values:
```
dax
EVALUATE ROW("Total", SUM('TableName'[Column]))
```

Group by and aggregate:
```
dax
EVALUATE SUMMARIZE('TableName', 'TableName'[GroupColumn], "Total", COUNTROWS('TableName'))
```

Top N rows:
```
dax
EVALUATE TOPN(10, 'TableName', 'TableName'[Column], DESC)
```

Distinct values:
```
dax
EVALUATE DISTINCT('TableName'[Column])
```

## Examples of DAX Queries

**Get all rows from a table:**
```
dax
EVALUATE 'TableName'
```

**Get specific columns:**
```
dax
EVALUATE
SELECTCOLUMNS(
    'ID',
    "client_asset_id", [cleint_asset_id],
    "Audit Result", [Audit Result],
    "Audit Remarks", [Audit Remarks]
)
```

**Filtered data:**
```
dax
EVALUATE
FILTER(
    'Assets',
    'Assets'[Audit Result] = "Validation Failed"
)
```

**Top N rows:**
```
dax
EVALUATE
TOPN(10, 'Assets', 'Assets'[Family Name], DESC)
```

## Output Format
{{"query_type":"question","confidence":0.95,"skills_to_use":["dax_query"],"skill_parameters":{{"dax_query":"YOUR_DAX_QUERY_HERE"}},"entities":{{"topics":[],"subjects":[]}},"reasoning":"brief reason"}}

