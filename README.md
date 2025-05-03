## **Automated Trading System in Interactive Brokers**

### _What is this?_

This is an implementation of a targeted volatility strategy on my paper trading account in Interactive Brokers for MES contracts.

It:
- Fetches historical data from IBKR for MES contracts
- Rolls the contract if it is 5 days away from expiry
- Forecasts volatility using a blended estimate of long and short term volatility, where short term volatility is calculated using an Exponentially Weighted Moving Average (EWMA) of volatility from the past 32 days
- Automatically rebalances the portfolio to meet target annual volatility of 20%
- Sends a Discord update on current positions, volatility fluctuations and portfolio performance

### _Why did I do this?_

This is a direct implementation of strategy 3 in Robert Carver's book, [Advanced Futures Trading Strategies](https://qoppac.blogspot.com/2023/04/advanced-futures-trading-strategies.html).
I thought it looked interesting, and I wanted to test a simple strategy on my paper trading account.
Would targeted volatility perform on its own, without the use of any factors (e.g. momentum, carry)? 
In the current situation, would it be able to save you from the drawdowns?

### _Thoughts after doing this?_

On the strategy:
- I don't know if his blended estimate formula or the use of EWMA to forecast volatility adds significant (or any) value to the strategy.
It could be overcomplicating things -- a simple moving average (using the last 2 months volatility) shows similar results in his book.  
- I'm executing his strategy exactly as described in his book to avoid my own biases. 
- The performance won't tell us much in the short term. Bad performance doesn't mean it doesn't work, good performance doesn't mean it works. 

On improvements/future projects:
- I'd like to continue implementing more advanced strategies in the book. Ideally there would be at least one of each factor to provide factor diversification.
- Ideally this program would run daily (except on days when the market is closed) at the same time. I have tried to do it with Task Scheduler -- but it does not work if your computer is switched off. 

Overall thoughts:
- I'm very excited to see how it performs!
- I've named it Hooky Pooky:

![Screenshot (23)](https://github.com/user-attachments/assets/0b3b0c3c-aa4e-4b1a-9f1b-8cbb5843d697)


### _How has Hooky Pooky performed so far?_

As of 2 May 2025, the portfolio is up 1.08% since inception. It was started 28 April 2025, so it has been active for ~5 days. 
Robert Carver's backtested results show a Sharpe Ratio of 0.48. Simple math tells us we can expect Hooky Pooky to delier a CAGR of 9.6% in the long term. I expect it to be lower, because (a) backtest results are usually higher, and (b) volatility drag.

If you made it here, thank you for reading! (I don't think anyone ever reads this.)
