- use blocks instead of lists 
- make sure we don't accidentally consider .default(None) as an error for actions that return optional values or None (see input and navigation actions)


- refactor actions to return a result with browser context as value?
    - instead of do f then g use f(g(x)) where f uses g as a parameter
    - not sure yet - read about kleisli composition
- add selenium browser driver 
- add puppeteer browser driver
- add crawlee browser driver

- create seperate pipeline for testing each driver implementation

