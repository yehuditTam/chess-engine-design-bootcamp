import tkinter as tk


def ask_player_names() -> tuple[str, str]:
    """Show a tkinter dialog and return (black_name, white_name)."""
    result = ["Black", "White"]

    root = tk.Tk()
    root.title("Kungfu Chess — Enter Player Names")
    root.resizable(False, False)

    tk.Label(root, text="Player 1 (Black):").grid(row=0, column=0, padx=10, pady=10, sticky="e")
    black_var = tk.StringVar()
    tk.Entry(root, textvariable=black_var, width=25).grid(row=0, column=1, padx=10)

    tk.Label(root, text="Player 2 (White):").grid(row=1, column=0, padx=10, pady=10, sticky="e")
    white_var = tk.StringVar()
    tk.Entry(root, textvariable=white_var, width=25).grid(row=1, column=1, padx=10)

    def on_start():
        result[0] = black_var.get().strip() or "Black"
        result[1] = white_var.get().strip() or "White"
        root.destroy()

    tk.Button(root, text="Start Game", command=on_start).grid(
        row=2, column=0, columnspan=2, pady=10
    )
    root.bind("<Return>", lambda _: on_start())
    root.mainloop()

    return result[0], result[1]
