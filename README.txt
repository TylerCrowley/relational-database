CS582 - Advanced Databse Systems

Set up instructions:
    1. Download and launch MySQL (https://www.mysql.com/)
    2. Run the command "source <PATH/TO/FILE>/setup.sql"
    3. Open a seperate terminal and run "python3 streamlit run <PATH/TO/FILE>/magicshop.py"

searchInventory(name=None, category=None, rarity=None, maxprice=None, minprice=None)
    - Returns a list of all items fitting that search, None means any for a given category
getItem(id)
    - Returns a single item, with the given item_id
order(adventurer_id, items)
    - Creates an order, given the id of the customer and a list of tuples containing the item_id and quantity ordered
getOrder(id)
    - Gets all information for a given order_id, including the items in it and the total cost
topSellers(days=0)
    - Shows the top selling items for a given period, 0 means all-time
refreshSummary()
    - Refreshes the 90 day summary table in memory
loggedIn(id)
    - Logs the id and time of any "log in"
getAdventurers()
    - Returns a list of all the customers
updateTotals()
    - Updates the total cost of each order, via the items in it and their cost
