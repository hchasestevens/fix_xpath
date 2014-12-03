fix_xpath
=========

Small module for fixing bracket mismatches in XPath expressions.

Example usage:
```python
>>> fix_brackets(".//div[contains(., 'xxx']")
".//div[contains(., 'xxx')]"
```
