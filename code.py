from ib_insync import *
from ib_insync import IB, Future, MarketOrder
import pandas as pd
import requests
from datetime import datetime
import pytz

# DO NOT RUN THIS CODE WHEN THE MARKETS ARE CLOSED. THE PROGRAM CANNOT FETCH THE LATEST PRICE DATA AND WILL WRONGLY EXECUTE THE TRADES. 

# establish connection with IB

ib = IB()
ib.connect('127.0.0.1',     # localhost IP
           7497,            # TWS paper trading account default no.
           clientId=1)      # any unique number

# returns qty of symbol contracts

def get_current_exposure(symbol):
    
    positions = ib.positions()
    curr_positions = [p for p in positions if p.contract.symbol == symbol]
    total_no_positions = sum(p.position for p in curr_positions)
    
    return total_no_positions

# get nearest expiry date of MES contracts

def get_expiry_date_of_X_nearest_MES_contract(x):
    
    mes_contract = Future(symbol='MES', exchange='CME', currency='USD')
    
    contracts = ib.reqContractDetails(mes_contract)             # get info for all MES contracts
     
    sorted_contracts = sorted(
        contracts, 
        key=lambda c: datetime.strptime(c.contract.lastTradeDateOrContractMonth, "%Y%m%d")
    )                                                           # sort contracts by expiry
    
    X_contract = sorted_contracts[x].contract
    X_expiry = X_contract.lastTradeDateOrContractMonth
    
    return X_expiry

# returns date of MES contract to trade

def get_contract_date():
    
    # contract expiry dates
    nearest_expiry = get_expiry_date_of_X_nearest_MES_contract(0)
    next_nearest_expiry = get_expiry_date_of_X_nearest_MES_contract(1)
    
    # convert nearest expiry date to comparable form
    expiry_date = datetime.strptime(nearest_expiry, "%Y%m%d").date()
    
    # current date
    toronto_tz = pytz.timezone('America/Toronto')
    current_datetime = datetime.now(toronto_tz)
    current_date = current_datetime.date()
    
    # compare the dates. if 5 days or less away from contract expiry, roll contract. 
    days_until_expiry = (expiry_date - current_date).days
    
    if days_until_expiry <= 5:
        return next_nearest_expiry
    else:
        return nearest_expiry

expiry_date = get_contract_date()

# gets expiry date of MES contracts currently holding

def get_MES_holding_expiry_date():
    
    positions = ib.positions()
    
    for position in positions:
        if position.contract.symbol == 'MES':
            expiry_date = position.contract.lastTradeDateOrContractMonth
        else:
            expiry_date = None
            
    return expiry_date

holdings_expiry = get_MES_holding_expiry_date()

# rolls if necessary

def roll_or_not():
    
    if holdings_expiry != expiry_date:
        return place_futures_order('MES', expiry_date, get_current_exposure('MES'), action='SELL', price=None)
    else:
        return None
    
roll_or_not()

# download data for MES and prepare

contract = Future(
    symbol='MES',
    lastTradeDateOrContractMonth=expiry_date,
    exchange='CME',
    currency='USD'
)
bars = ib.reqHistoricalData(
    contract,
    endDateTime='',
    durationStr='1 Y',
    barSizeSetting='1 day',
    whatToShow='TRADES',
    useRTH=False,
    formatDate=1
)
df = util.df(bars)                                        # Convert to DataFrame
df['daily_returns'] = df['close'].pct_change()
window = df['daily_returns'].tail(32)                     # last 32 days

# calculate mean daily return, EWMA

def EWMA_mean_return(span, arr):
    
    sum = 0
    mult = 1
    lamb = 2 / (span + 1)           # lambda value
    rarr = arr[::-1]                # reverse the array of values
    
    for value in rarr:
        
        sum += mult * value         # add new value to sum
        mult = mult * (1 - lamb)           # update value of mult
    
    sum = sum * lamb                # multiply everything by lambda at the end
    
    return sum

# calculate mean daily standard deviation, EWMA

def EWMA_sd(ewma_ret_avg, arr, span):
    
    sum = 0
    mult = 1
    lamb = 2 / (span + 1)           # lambda value
    rarr = arr[::-1]                # reverse the array of values
    
    for value in rarr:
        
        sum += ((value - ewma_ret_avg) ** 2) * mult
        mult = mult * (1 - lamb)
        
    sum = sum * lamb
    sum = sum ** 0.5
    
    return sum

# convert daily standard deviation to annual

def annualised_sd(daily_sd):
    
    return daily_sd * (252 ** 0.5)

# calculate stats
    
ewma_mean_ret = EWMA_mean_return(32, window)
print("The Exponentially Weighted Moving Average (EWMA) of daily return is: ", ewma_mean_ret)

ewma_sd = EWMA_sd(ewma_mean_ret, window, 32)
print("The Exponentially Weighted Moving Average (EWMA) of daily standard deviation is: ", ewma_sd)

st_avg = annualised_sd(ewma_sd)
print("The Exponentially Weighted Moving Average (EWMA) of annual standard deviation is: ", st_avg)

# define last 10 year average annual standard deviation of MES contract price

LT_AVG_SD = 0.18

# RC's formula of blended estimate of long and short term standard deviations to forecast

def blended_estimate(lt_avg, st_avg):
    
    return (0.3 * lt_avg) + (0.7 * st_avg)

sd_estimate = blended_estimate(LT_AVG_SD, st_avg)
print("The blended estimate of annual standard deviation, using a weight of 0.3 \
to the 10 year average and 0.7 to the short term (past 32 days) is:  ", sd_estimate)

# calculate amount of available funds in IB account

def get_nlv():
    
    account_summary = ib.accountSummary()
    
    for item in account_summary:
        if item.tag == 'NetLiquidation':
            nlv = float(item.value)
            
    return nlv

nlv = get_nlv()
print("The available funds in the IB account: ", get_nlv())

# get delayed (15 mins) price of an MES futures contract

def get_MES_price():
    
    ib.reqMarketDataType(3)         # delayed data so 3
    
    contract = Future(
    symbol='MES',         
    exchange='CME',      
    lastTradeDateOrContractMonth=expiry_date,  # Format: YYYYMM or YYYYMMDD
    currency='USD')
    
    ticker = ib.reqMktData(contract, '', False, False)
    
    ib.sleep(2)
    
    delayed_ask_price = ticker.ask
    
    print(f"Delayed Last Price: {ticker.last}")
    print(f"Delayed Bid Price: {ticker.bid}")
    print(f"Delayed Ask Price: {ticker.ask}")
    
    return delayed_ask_price
    
delayed_ask_price = get_MES_price()
print("The delayed (15 minutes) ask price of an MES futures contract: ", delayed_ask_price)

# calculates the ideal exposure for portfolio

TARGET_VOL = 0.20

def get_exposure(target_vol, actual_vol, nlv):
    
    m = target_vol/actual_vol
    
    Ideal_exposure = m * float(nlv)
    return Ideal_exposure

ideal_exposure = get_exposure(TARGET_VOL, sd_estimate, nlv)
print("The ideal exposure based on current amounts of capital: ", ideal_exposure)

# calculates num of contracts to hold

def get_no_of_contracts(contract_price, multiplier, ideal_exposure):
    
    notional_exposure = contract_price * multiplier
    
    return (ideal_exposure / notional_exposure)

MES_MULTIPLIER = 5

ideal_no_of_contracts = get_no_of_contracts(delayed_ask_price, MES_MULTIPLIER, ideal_exposure)
print("The ideal number of contracts to hold today: ", ideal_no_of_contracts)

# rounds the number of contracts to integer

def round_value(num_of_contracts):
    
    if (num_of_contracts % 1) >= 0.5:
        return int(num_of_contracts) + 1
    else:
        return int(num_of_contracts)
    
num_of_contracts_int = round_value(ideal_no_of_contracts)
print("The ideal number of contracts to hold today, rounded: ", num_of_contracts_int)

# ContractSymbol (str) -> NumberofContractsHeld (int)

def get_current_exposure(symbol):
    
    positions = ib.positions()
    curr_positions = [p for p in positions if p.contract.symbol == symbol]
    total_no_positions = sum(p.position for p in curr_positions)
    
    return total_no_positions

print("The number of MES contracts you are currently holding: ", get_current_exposure('MES'))

# places IBKR order
    
def place_futures_order(symbol, expiry, quantity, action='BUY', price=None):
    """
    Place an order for a specified number of futures contracts.

    :param symbol: str, the futures contract symbol (e.g., 'MES')
    :param expiry: str, expiry date in 'YYYYMM' format (e.g., '202506')
    :param quantity: int, number of contracts to trade
    :param action: str, 'BUY' or 'SELL'
    :param price: float, limit price (optional; if None, a market order is placed)
    :return: Trade object representing the placed order
    """

    # Define the futures contract
    contract = Future(
        symbol=symbol,
        lastTradeDateOrContractMonth=expiry,
        exchange='CME',
        currency='USD'
    )

    # Qualify the contract (ensures contract details are valid)
    ib.qualifyContracts(contract)

    # Create the order
    if price is None:
        order = MarketOrder(action, quantity)
    else:
        order = LimitOrder(action, quantity, price)

    # Place the order
    trade = ib.placeOrder(contract, order)

    # Wait for the order to be processed
    ib.sleep(2)

    return trade

# time to trade

def trade(current_num_of_contracts, ideal_num_of_contracts):
    
    diff = ideal_num_of_contracts - current_num_of_contracts
    
    if diff > 0:
        amt = diff
        return place_futures_order('MES', expiry_date, amt, action='BUY', price=None)
    elif diff < 0:
        amt = -diff
        return place_futures_order('MES', expiry_date, amt, action='SELL', price=None)
    else:
        return None
    
#### TRADE!!!
    
trade(get_current_exposure('MES'), num_of_contracts_int)
    
# time for update! (futures market sunday-friday 5pm - 4pm)

WEBHOOK_URL = "Censored."

# timestamps

toronto_tz = pytz.timezone('America/Toronto')
toronto_time = datetime.now(toronto_tz)

day_of_week = toronto_time.strftime('%A')                
day = toronto_time.strftime('%d').lstrip('0')            
month = toronto_time.strftime('%B')                      
year = toronto_time.strftime('%Y')                      
time_formatted = toronto_time.strftime('%I:%M %p').lstrip('0') 

# get mkt value of mes contracts

def get_mes_mktval():
    
    portfolio = ib.portfolio()
    
    for item in portfolio:
        
        if item.contract.symbol == "MES":  
            mkt_val = item.marketValue
                
    return mkt_val

# find amt of available funds in account

def get_available_funds():
    
    account_summary = ib.accountSummary()
    
    for item in account_summary:
        if item.tag == 'AvailableFunds':
            avail_funds = float(item.value)
            
    return avail_funds

# some numbers for message

CURR_NLV = float(get_nlv())
START_VALUE = 102410.13
PERFORMANCE = round((CURR_NLV - START_VALUE) / START_VALUE, 4)
LEVERAGE_AMT = round(ideal_exposure/CURR_NLV, 4)

if PERFORMANCE > 0:
    direction = 'up!'
elif PERFORMANCE < 0:
    direction = 'down...'
else:
    direction = 'neutral.'
    
NUM_OF_MES = int(get_current_exposure('MES'))
AVAIL_FUNDS = get_available_funds()

BLEND = round(sd_estimate, 4)
EWMA_ANN_SD = round(st_avg, 4)

EXPIRY_DATE = get_MES_holding_expiry_date()
MKT_VAL = get_mes_mktval()

ACTUAL_LEV = round(MKT_VAL/CURR_NLV, 4)

# message

message = f"""
__________________________________________________________________________
Welcome to a new day. 

Date: {day_of_week}, {day} {month} {year}.
Time: {time_formatted} EDT (Toronto time).

Starting net liquidation value of portfolio (28 Apr 2025): {START_VALUE}
Current net liquidation value of portfolio: {CURR_NLV}
Performance since inception: {PERFORMANCE}

Target annual standard deviation: {TARGET_VOL}
EWMA annual standard deviation (based on past 32 days): {EWMA_ANN_SD}
RC's blended estimate of standard deviation: {BLEND}

Ideal leverage amount (where 1 is no leverage): {LEVERAGE_AMT}
Actual leverage amount: {ACTUAL_LEV}

Current holdings: 
{NUM_OF_MES} MES contracts ({EXPIRY_DATE}), market value: {MKT_VAL}
Available funds (NLV - Current initial margin): {AVAIL_FUNDS}
  
We are {direction}
__________________________________________________________________________
"""

# Market value: {MKT_VAL}
# Actual leverage amount: {ACTUAL_LEV}

# send out message

data = {
    "content": message
}
response = requests.post(WEBHOOK_URL, json=data)

if response.status_code == 204:
    print("Update sent successfully.")
else:
    print(f"Failed to send update: {response.status_code}, {response.text}")

# # disconnect session

# ib.disconnect()
