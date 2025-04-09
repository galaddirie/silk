- use blocks instead of lists 
- make sure we don't accidentally consider .default(None) as an error for actions that return optional values or None (see input and navigation actions)



- add selenium browser driver 
- add puppeteer browser driver
- add crawlee browser driver

- create seperate pipeline for testing each driver implementation



- lets clean up modal/type defs ex users should call actions.base for action generic, users shouldnt need to type action defaults anyway

- a if else flow action would be nice ex If(condition, then) ElseIf(condition, then) Else(then), at min If would be nice to compliment branch, if could be an alias for a branch with no false action




- options  for actions should be more observable




- advertise smart defaults ex you dont need to specific Click(options={"delay": 0.5, "move_to": True}) if you want to click an element


-branch should work on exceptions and fasly values,


- we should have an action that throws an error if false
  cal it assert? asset asset()


- for mapped tasks theses should be parallel tasks 

maybe for mapped tasks we do the following 

QueryAll >> [Filter], anything in the [] is the sub graph run for each item in the list from the QueryAll

we likely need to do  Mapped(Filter)

- improve data extraction



- expand extration actions to include ExtractToModel(dict, model) --> Result[T<model>,Exception]


- we need to think about how to chain actions to pydantic models



- import model/type exports ex we have silk.models.browser and silk.actions.base
- we need to have a uniform place for our types