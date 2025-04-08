- use blocks instead of lists 
- make sure we don't accidentally consider .default(None) as an error for actions that return optional values or None (see input and navigation actions)


- refactor actions to return a result with browser context as value?
    - instead of do f then g use f(g(x)) where f uses g as a parameter
    - not sure yet - read about kleisli composition
- add selenium browser driver 
- add puppeteer browser driver
- add crawlee browser driver

- create seperate pipeline for testing each driver implementation

- FIX selectors.selector import it should be from .selectors import *

-fix action decorator so its not @action() but @action 

- move WaitForSelector to extraction from navigation

- lets clean up modal/type defs ex users should call actions.base for action generic, users shouldnt need to type action defaults anyway

- a if else flow action would be nice ex If(condition, then) ElseIf(condition, then) Else(then), at min If would be nice to compliment branch, if could be an alias for a branch with no false action

- move log to actions.log from actions.flow


- input actions should be able to accept element values

- options  for actions should be more observable


- should custom actions return actions?

@action()
def Login(context: ActionContext, username: str, password: str):
    if not username or not password:
        return Error("Username and password are required")
    pipeline: Action[None] = (
        Navigate(selectors.LOGIN_URL)
        >> wait(2)
        >> WaitForSelector(selectors.LoginModal.USERNAME_INPUT)
        >> Fill(selectors.LoginModal.USERNAME_INPUT, username, options={"delay": 0.5, "timeout": 10000, "click": True, "focus": True})
        >> Fill(selectors.LoginModal.PASSWORD_INPUT, password)
        >> Click(selectors.LoginModal.LOGIN_BUTTON)
    )

    return pipeline

- how do we forward to sub actions

@action()
def CloseModals(context: ActionContext):  # how do we forward the context?
    pipeline: Action[None] = If(
        ElementExists(selectors.LoginModal.MODAL),
        Click(selectors.LoginModal.MODAL),
    ) >> If(
        ElementExists(selectors.CAPTCHA),
        Click(selectors.CAPTCHA),
    )


- advertise smart defaults ex you dont need to specific Click(options={"delay": 0.5, "move_to": True}) if you want to click an element


-branch should work on exceptions and fasly values,

- element exists should throw an error?

- we should have an action that throws an error if false
  cal it assert? asset asset()


- for mapped tasks theses should be parallel tasks 

maybe for mapped tasks we do the following 

QueryAll > [Filter], anything in the [] is the sub graph run for each item in the list from the QueryAll

- improve data extraction


- we need too convert function from function to action class to get access to bitwise operators


- use > and <  to replace current  >> and <<, now  >> will  forward the data and the context, > will just forward the context

- expand extration actions to include ExtractToModel(dict, model) --> Result[T<model>,Exception]


- we need to think about how to chain actions to pydantic models


- IDEA BIG,  if action need a parameter and isnt supplied we use previous result as the parameter

example
try_to_open_search_sheet: Action[None] = (
        ElementExists(selectors.SEARCH_OPEN) >> 
        QueryAll(selectors.SEARCH_OPEN) >>
        Click() # this will use the previous result as the parameter BUT IF WE ADD selector ex
        Click(selectors.SEARCH_OPEN) # this will selector instead of previous result
    )
    