import yfinance as yf
import concurrent.futures
import json
import time
import os

### CONFIG ###
TICKER_SYMBOLS = ["HCMC", "ATVK", "ACB"]
LOGGING_LEVEL = 0
CHECK_INTERVAL = 60     # number of seconds between each price check

# MESSAGES CONFIG #
PRICE_ALERT_PERCENTAGE = 5
# PRICE_ALERT_MESSAGE = "Price alert: ticker symbol {} {} {}% since last price alert to price {} {}"  #format with ticker_symbol up/down percentage price currency
PRICE_ALERT_MESSAGE = "Price alert: ticker symbol {} {} {}% / {} {} since last price alert to price {} {}\n{} {}% / {} {} since market open"
PRICE_ALERT_MESSAGE = "Price alert: ticker symbol {} {} {}% since last announced\n\n{} {}% since market open"

PRE_MARKET_MESSAGE = ""
MARKET_CLOSE_MESSAGE = ""

PERCENTAGE_DECIMAL_PLACES = 2  # number of decimal places after percentage. e.g. 3 = 2.51%

# SIGNAL-CLI CONFIG #
GROUPS = os.getenv("SIGNAL_CLI_GROUPS")       # single string of group ids, space separated (i think)
USERNAME = os.getenv("SIGNAL_CLI_USERNAME")      # phone number in international format

### END CONFIG ###


def get_current_price(symbol):
	ticker = yf.Ticker(symbol)
	todays_data = ticker.history(period='1d')
	return todays_data['Close'][0]


class Instrument:
	def __init__(self, ticker_symbol):
		self.ticker = yf.Ticker(ticker_symbol)
		self.ticker_info = self.ticker.info
		self.update_price()
		self.last_announced_price = self.ticker_info['currentPrice']

		if LOGGING_LEVEL:
			print("constructor for ticker symbol {}, info = {}\nlast_announced_price = {}".format(
				ticker_symbol, json.dumps(self.ticker_info, indent=4), self.last_announced_price))

	def update_price(self):
		# not returned by the api but important
		self.ticker_info['currentPrice'] = self.ticker.history(period="1d")[
			'Close'][0]

	def update_info(self):
		self.ticker = yf.Ticker(self.ticker_info['symbol'])
		self.ticker_info = self.ticker.info
		self.update_price()
		print("ticker symbol {} updated, last_announced_price = {}, currentPrice = {}".format(
			self.ticker_info['symbol'], self.last_announced_price, self.ticker_info['currentPrice']))
		return

	def alert_price_change_if_needed(self):
		#        percentage_difference = (1 - (self.last_announced_price / self.ticker_info['currentPrice']))

		# last announced price is always the one that is compared, e.g. if last announced price = 10 and new price = 12 that's a 20% gain
		percentage_difference_since_last_announced = percentage_difference(self.ticker_info['currentPrice'], self.last_announced_price)
#change_percent = ((float(current)-previous)/previous)*100
		if percentage_difference_since_last_announced < 0:
			up_or_down_since_last_announced = "down"
		else:        # must be down
			up_or_down_since_last_announced = "up"
		percentage_difference_since_last_announced = abs(percentage_difference_since_last_announced)
		if percentage_difference_since_last_announced >= PRICE_ALERT_PERCENTAGE:
			# need to send price alert
			self.last_announced_price = self.ticker_info['currentPrice']
			percentage_difference_since_market_open = percentage_difference(
				self.ticker_info['currentPrice'], self.ticker_info['open'])
			# up or down for since_market_open
			if percentage_difference_since_market_open < 0:
				up_or_down_since_open = "down"
			else:
				up_or_down_since_open = "up"
			percentage_difference_since_market_open = round(
				abs(percentage_difference_since_market_open), PERCENTAGE_DECIMAL_PLACES)

			# format message
			''' format arguments are:
				1. ticker symbol
				2. up or down since last announced price
				3. percentage change since last announced price
				4. up or down since market open
				5. percentage change since market open
			'''
			temp_message = PRICE_ALERT_MESSAGE.format(self.ticker_info['symbol'],
													up_or_down_since_last_announced,
													percentage_difference_since_last_announced,
													up_or_down_since_open,
													percentage_difference_since_market_open
												)

			print("alerting")
			self.send_message(temp_message)

	def send_message(self, message):
		temp_message = "signal-cli -u '{}' send -g '{}' -m '{}'".format(
			USERNAME, GROUPS, message)
		print("sending message {}".format(temp_message))
		os.system(temp_message)

	# for debug / testing purposes

	def say_hello(self):
		print("hello from Instrument class!")


def percentage_difference(number1, number2):
	if (number1 == number2):
		return 0
	difference = round(((number1 - number2) / number2) * 100, PERCENTAGE_DECIMAL_PLACES)
	print("percentage difference between {} and {} is {}".format(number1, number2, difference))

	return difference


def market_close_report(stocks_list_us):
	return


def pre_market_report(stocks_list_us):
	return

def init_all(tickers):
	tickers_list = []
	with concurrent.futures.ThreadPoolExecutor(
			max_workers = len(tickers)
		) as executor:
			futures = {executor.submit(
				Instrument, ticker): ticker for ticker in tickers}

	for future in concurrent.futures.as_completed(futures):
		tickers_list.append(future.result())
	return tickers_list



def main():
	ticker_list = init_all(TICKER_SYMBOLS)
	while True:
		print("------------------------------------- updating info -------------------------------------")
		with concurrent.futures.ThreadPoolExecutor(
			max_workers=len(ticker_list)
		) as executor:
			{executor.submit(stock.update_info): stock for stock in ticker_list}
		print("------------------------------------- end updating info -------------------------------------")

		for ticker in ticker_list:
			ticker.alert_price_change_if_needed()

		time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
	main()

