from __future__ import annotations

import queue
import threading
import tkinter as tk
from tkinter import messagebox, scrolledtext

from .importer import ImportRuntime, run_import_from_text_with_options


def launch_gui() -> None:
    root = tk.Tk()
    root.title("KNI Zotero Importer")
    root.geometry("980x760")

    instructions = tk.Label(
        root,
        text="Paste structured entries below. Supported fields: Collection, PMID, Title, Tags, Note, Type, URL, DOI, ISBN.",
        anchor="w",
        justify="left",
    )
    instructions.pack(fill="x", padx=12, pady=(12, 6))

    editor = scrolledtext.ScrolledText(root, wrap=tk.WORD, font=("Menlo", 12))
    editor.pack(fill="both", expand=True, padx=12, pady=6)

    options_frame = tk.Frame(root)
    options_frame.pack(fill="x", padx=12, pady=6)

    dry_run = tk.BooleanVar(value=False)
    tk.Checkbutton(options_frame, text="Dry run", variable=dry_run).pack(side="left")
    create_missing_collections = tk.BooleanVar(value=False)
    tk.Checkbutton(options_frame, text="Create Missing Collections", variable=create_missing_collections).pack(side="left", padx=(8, 0))
    status_var = tk.StringVar(value="Ready.")
    status_label = tk.Label(options_frame, textvariable=status_var, anchor="w")
    status_label.pack(side="left", padx=(12, 0))

    output = scrolledtext.ScrolledText(root, wrap=tk.WORD, height=14, font=("Menlo", 11))
    output.pack(fill="both", expand=False, padx=12, pady=(6, 12))
    result_queue: queue.Queue[tuple[str, object]] = queue.Queue()
    import_running = {"value": False}
    runtime_holder: dict[str, ImportRuntime | None] = {"value": None}

    def set_busy(is_busy: bool) -> None:
        import_running["value"] = is_busy
        state = tk.DISABLED if is_busy else tk.NORMAL
        import_button.config(state=state)
        refresh_button.config(state=state)
        sample_button.config(state=state)
        clear_button.config(state=state)

    def poll_results() -> None:
        try:
            kind, payload = result_queue.get_nowait()
        except queue.Empty:
            if import_running["value"]:
                root.after(150, poll_results)
            return
        set_busy(False)
        if kind == "error":
            status_var.set("Import failed.")
            messagebox.showerror("KNI Zotero Importer", str(payload))
            return
        if kind == "refresh":
            count = payload
            status_var.set(f"Collections refreshed. {count} total collections loaded.")
            output.delete("1.0", tk.END)
            messagebox.showinfo("KNI Zotero Importer", f"Refreshed collection list. {count} total Zotero collections loaded.")
            return
        report = payload
        output.delete("1.0", tk.END)
        output.insert(tk.END, report.render_text())
        if report.has_errors:
            status_var.set("Import completed with errors.")
            messagebox.showwarning("KNI Zotero Importer", "Import completed with errors. See the output pane and logs/errors.csv.")
        else:
            status_var.set("Import completed.")
            messagebox.showinfo("KNI Zotero Importer", "Import completed.")

    def run_import_worker(text: str, dry_run_enabled: bool, create_missing_enabled: bool) -> None:
        try:
            if runtime_holder["value"] is None:
                runtime_holder["value"] = ImportRuntime.from_env()
            report = run_import_from_text_with_options(
                text=text,
                dry_run=dry_run_enabled,
                runtime=runtime_holder["value"],
                create_missing_collections=create_missing_enabled,
            )
        except Exception as exc:
            result_queue.put(("error", exc))
            return
        result_queue.put(("report", report))

    def do_import() -> None:
        if import_running["value"]:
            return
        text = editor.get("1.0", tk.END).strip()
        if not text:
            messagebox.showerror("KNI Zotero Importer", "Paste at least one entry before importing.")
            return
        output.delete("1.0", tk.END)
        output.insert(tk.END, "Import running in background...\n")
        status_var.set("Import running...")
        set_busy(True)
        worker = threading.Thread(
            target=run_import_worker,
            args=(text, dry_run.get(), create_missing_collections.get()),
            daemon=True,
        )
        worker.start()
        root.after(150, poll_results)

    def run_refresh_collections_worker() -> None:
        try:
            if runtime_holder["value"] is None:
                runtime_holder["value"] = ImportRuntime.from_env()
            collections = runtime_holder["value"].refresh_collections()
        except Exception as exc:
            result_queue.put(("error", exc))
            return
        result_queue.put(("refresh", len(collections)))

    def refresh_collections() -> None:
        if import_running["value"]:
            return
        status_var.set("Refreshing collections...")
        set_busy(True)
        worker = threading.Thread(target=run_refresh_collections_worker, daemon=True)
        worker.start()
        root.after(150, poll_results)

    def load_sample() -> None:
        sample = (
            "Collection: 00 KNI - Foundational Texts & Major Reviews\n"
            "PMID: 8632988\n"
            "Tags: seminal; biomarker-neuroimaging\n"
            "Note: Early structural MRI anchor paper linking recurrent MDD with hippocampal atrophy.\n\n"
            "Collection: PMC (recent, interesting)\n"
            "Type: blog post\n"
            "Title: Example implementation note\n"
            "URL: https://example.org/implementation-note\n"
            "Tags: commentary; implementation\n"
            "Note: Example of a non-PubMed source with URL-driven import.\n"
        )
        editor.delete("1.0", tk.END)
        editor.insert(tk.END, sample)

    buttons = tk.Frame(root)
    buttons.pack(fill="x", padx=12, pady=(0, 12))
    import_button = tk.Button(buttons, text="Import", command=do_import)
    import_button.pack(side="left")
    refresh_button = tk.Button(buttons, text="Refresh Collections", command=refresh_collections)
    refresh_button.pack(side="left", padx=8)
    sample_button = tk.Button(buttons, text="Load Sample", command=load_sample)
    sample_button.pack(side="left")
    clear_button = tk.Button(buttons, text="Clear", command=lambda: editor.delete("1.0", tk.END))
    clear_button.pack(side="left", padx=8)

    root.mainloop()
