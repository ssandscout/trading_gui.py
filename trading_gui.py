import tkinter as tk
from tkinter import ttk
import pika
import threading
import json

# ====================== #
#   "Gen Z" Color Theme  #
# ====================== #
BG_COLOR = "#121212"        # Main background
TEXT_COLOR = "#EEEEEE"      # Main text color
ACCENT_COLOR = "#FF007F"    # Pink accent color

# ======================= #
#   RabbitMQ Constants    #
# ======================= #
RABBITMQ_HOST = "localhost"
RABBITMQ_PORT = 5672
TRADES_QUEUE = "trades"

class TradingGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Gen Z Trading Monitor 📈")
        self.root.config(bg=BG_COLOR)

        # Dictionary to store last prices for each symbol
        self.last_prices = {}

        # Create a style for the dark theme (ttk widgets)
        self._setup_style()

        # Configure the grid so that row 1 and column 0 can expand
        self.root.rowconfigure(1, weight=1)
        self.root.columnconfigure(0, weight=1)

        # Build the main UI
        self._build_ui()

        # Set up RabbitMQ connection and consumer
        self._setup_rabbitmq()

    def _setup_style(self):
        """Configure a custom dark theme with a pink accent for ttk."""
        style = ttk.Style(self.root)
        style.theme_use("clam")

        style.configure(
            "GenZ.Treeview",
            background="#222",
            fieldbackground="#222",
            foreground=TEXT_COLOR,
            rowheight=25,
            borderwidth=0
        )

        style.configure(
            "GenZ.Treeview.Heading",
            background=ACCENT_COLOR,
            foreground="#FFFFFF",
            font=("Helvetica", 12, "bold")
        )

        style.map("GenZ.Treeview", background=[("selected", "#444")])

    def _build_ui(self):
        """Build UI elements (grid layout) with two Treeviews: Trades and Last Prices."""
        # Real-Time Trades label (centered)
        header_label = tk.Label(
            self.root,
            text="Real-Time Trades (Grid View)",
            font=("Helvetica", 16, "bold"),
            fg=ACCENT_COLOR,
            bg=BG_COLOR,
            anchor="center"
        )
        header_label.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="ew")

        # Frame for the trades Treeview
        trades_frame = ttk.Frame(self.root)
        trades_frame.grid(row=1, column=0, padx=10, pady=5, sticky="nsew")

        trades_scrollbar = ttk.Scrollbar(trades_frame, orient="vertical")
        trades_scrollbar.pack(side="right", fill="y")

        self.trades_tree = ttk.Treeview(
            trades_frame,
            columns=("symbol", "price", "quantity", "buyer", "seller"),
            show="headings",
            yscrollcommand=trades_scrollbar.set,
            style="GenZ.Treeview"
        )
        self.trades_tree.pack(side="left", fill="both", expand=True)
        trades_scrollbar.config(command=self.trades_tree.yview)

        # Set up column headings
        self.trades_tree.heading("symbol", text="Symbol")
        self.trades_tree.heading("price", text="Price")
        self.trades_tree.heading("quantity", text="Qty")
        self.trades_tree.heading("buyer", text="Buyer")
        self.trades_tree.heading("seller", text="Seller")

        # Optional column widths
        self.trades_tree.column("symbol", width=80)
        self.trades_tree.column("price", width=80)
        self.trades_tree.column("quantity", width=80)
        self.trades_tree.column("buyer", width=120)
        self.trades_tree.column("seller", width=120)

        # Last Prices label (centered)
        last_prices_label = tk.Label(
            self.root,
            text="Last Prices",
            font=("Helvetica", 14, "bold"),
            fg=ACCENT_COLOR,
            bg=BG_COLOR,
            anchor="center"
        )
        last_prices_label.grid(row=2, column=0, padx=10, pady=(10, 5), sticky="ew")

        # Frame for the last prices Treeview
        prices_frame = ttk.Frame(self.root)
        prices_frame.grid(row=3, column=0, padx=10, pady=5, sticky="nsew")

        prices_scrollbar = ttk.Scrollbar(prices_frame, orient="vertical")
        prices_scrollbar.pack(side="right", fill="y")

        self.prices_tree = ttk.Treeview(
            prices_frame,
            columns=("symbol", "last_price"),
            show="headings",
            yscrollcommand=prices_scrollbar.set,
            style="GenZ.Treeview"
        )
        self.prices_tree.pack(side="left", fill="both", expand=True)
        prices_scrollbar.config(command=self.prices_tree.yview)

        self.prices_tree.heading("symbol", text="Symbol")
        self.prices_tree.heading("last_price", text="Last Price")
        self.prices_tree.column("symbol", width=80)
        self.prices_tree.column("last_price", width=100)

        # Close button
        close_button = tk.Button(
            self.root,
            text="Close",
            font=("Helvetica", 12, "bold"),
            bg=ACCENT_COLOR,
            fg="#ffffff",
            command=self.on_closing
        )
        close_button.grid(row=4, column=0, padx=10, pady=10, sticky="e")

    def _setup_rabbitmq(self):
        """Connect to RabbitMQ and start consuming messages from the 'trades' queue."""
        self.connection = pika.BlockingConnection(
            pika.ConnectionParameters(host=RABBITMQ_HOST, port=RABBITMQ_PORT)
        )
        self.channel = self.connection.channel()

        self.channel.queue_declare(queue=TRADES_QUEUE)

        listen_thread = threading.Thread(target=self._receive_trades, daemon=True)
        listen_thread.start()

    def _receive_trades(self):
        """Consume messages from the 'trades' queue."""
        def callback(ch, method, properties, body):
            try:
                trade = json.loads(body.decode("utf-8"))
                self.root.after(0, self._process_trade, trade)
            except Exception as e:
                print("Error decoding trade:", e)
            ch.basic_ack(delivery_tag=method.delivery_tag)

        self.channel.basic_consume(
            queue=TRADES_QUEUE,
            on_message_callback=callback,
            auto_ack=False
        )
        print(" [*] Listening for trades in TRADES_QUEUE...")
        self.channel.start_consuming()

    def _process_trade(self, trade):
        """Update the trades table and the last price table upon receiving a new trade."""
        symbol = trade.get("symbol", "???")
        price = trade.get("price", 0.0)
        quantity = trade.get("quantity", 0)
        buyer = trade.get("buyer", "???")
        seller = trade.get("seller", "???")

        # Add a new row to the trades table
        self.trades_tree.insert(
            "", tk.END,
            values=(symbol, price, quantity, buyer, seller)
        )

        # Update the last price for this symbol
        self.last_prices[symbol] = price
        self._refresh_prices_tree()

    def _refresh_prices_tree(self):
        """Clear the last prices table and repopulate it with the updated prices."""
        for item in self.prices_tree.get_children():
            self.prices_tree.delete(item)

        for symbol, price in self.last_prices.items():
            self.prices_tree.insert("", tk.END, values=(symbol, price))

    def on_closing(self):
        """Stop consuming messages and close the connection before destroying the window."""
        print("Closing GUI...")
        try:
            self.channel.stop_consuming()
            self.connection.close()
        except:
            pass
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    root.geometry("700x600")
    app = TradingGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()
