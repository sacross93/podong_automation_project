import tkinter as tk

class CategoryWindow(tk.Frame):
    def __init__(self, master):
        super().__init__(master)
        self.master = master
        self.master.title("Category Window")

        self.category_listbox = tk.Listbox(self.master)
        self.category_listbox.pack(side="left", padx=10, pady=10, fill="both", expand=True)

        scrollbar = tk.Scrollbar(self.master)
        scrollbar.pack(side="right", padx=(0, 10), pady=10, fill="y")

        self.category_listbox.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.category_listbox.yview)

        frame_buttons = tk.Frame(self.master)
        frame_buttons.pack(padx=10, pady=(0, 10))

        self.select_button = tk.Button(frame_buttons, text="Select", command=self.select_category)
        self.select_button.pack(side="left", padx=5)

        self.delete_button = tk.Button(frame_buttons, text="Delete", command=self.delete_category)
        self.delete_button.pack(side="left", padx=5)

        self.rename_button = tk.Button(frame_buttons, text="Rename", command=self.rename_category)
        self.rename_button.pack(side="left", padx=5)

        self.selected_category = None

    def update_categories(self, categories):
        self.category_listbox.delete(0, END)
        for category in categories:
            self.category_listbox.insert(END, category)
        self.category_listbox.yview_moveto(0)  # Set scrollbar position to top

    def select_category(self):
        selected_index = self.category_listbox.curselection()
        if selected_index:
            self.selected_category = self.category_listbox.get(selected_index)
            content_window.update_content(data.get(self.selected_category, ""))
            status_label.config(text=f"Selected Category: {self.selected_category}")
        else:
            status_label.config(text="No Category Selected")

    def delete_category(self):
        selected_index = self.category_listbox.curselection()
        if selected_index:
            selected_category = self.category_listbox.get(selected_index)
            response = tk.messagebox.askyesno(
                "Delete Category", f"Are you sure you want to delete the category '{selected_category}'?"
            )
            if response:
                del data[selected_category]
                save_data_to_excel()
                self.update_categories(data.keys())
                content_window.update_content("")
                status_label.config(text="Category Deleted")
        else:
            status_label.config(text="No Category Selected")

    def rename_category(self):
        selected_index = self.category_listbox.curselection()
        if selected_index:
            selected_category = self.category_listbox.get(selected_index)
            new_category = tk.simpledialog.askstring(
                "Rename Category", f"Enter a new name for the category '{selected_category}':"
            )
            if new_category:
                data[new_category] = data.pop(selected_category)
                save_data_to_excel()
                self.update_categories(data.keys())
                content_window.update_content(data.get(new_category, ""))
                status_label.config(text=f"Category '{selected_category}' renamed to '{new_category}'")
        else:
            status_label.config(text="No Category Selected")

