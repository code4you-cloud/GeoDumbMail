import ast

class DjangoViewAnalyzer(ast.NodeVisitor):

    def __init__(self):
        # Nome funzione -> nodo AST
        self.functions = {}
        # Nome funzione -> lista di nomi di funzioni chiamate al suo interno
        self.calls = {}
        self.current_function = None

    def visit_FunctionDef(self, node):
        func_name = node.name
        self.functions[func_name] = node
        self.calls[func_name] = []

        previous_function = self.current_function
        self.current_function = func_name

        self.generic_visit(node)

        self.current_function = previous_function

    def visit_Call(self, node):
        if self.current_function:
            # Chiamata diretta: funzione()
            if isinstance(node.func, ast.Name):
                self.calls[self.current_function].append(node.func.id)
            # Chiamata di metodo: self.funzione() o modulo.funzione()
            elif isinstance(node.func, ast.Attribute):
                self.calls[self.current_function].append(node.func.attr)

        self.generic_visit(node)


def analizza_views(percorso_file, master_func="master"):

    with open(percorso_file, "r", encoding="utf-8") as f:
        tree = ast.parse(f.read(), filename=percorso_file)

    analyzer = DjangoViewAnalyzer()
    analyzer.visit(tree)

    print("=== A. FUNZIONI E METODI INDIVIDUATI ===")
    if not analyzer.functions:
        print("Nessuna funzione trovata nel file.")
        return

    for func in analyzer.functions:
        print(f" - {func}")

    print("\n=== B. ANALISI DELLA FUNZIONE MASTER ===")
    if master_func not in analyzer.functions:
        print(f"La funzione master '{master_func}' NON esiste nel file.")
        return

    print(f"La funzione '{master_func}' è stata trovata.")
    chiamate_master = analyzer.calls.get(master_func, [])

    # Filtra solo le chiamate che corrispondono a funzioni definite nello stesso file
    chiamate_interne = [
        f for f in chiamate_master if f in analyzer.functions and f != master_func
    ]

    if chiamate_interne:
        print(f"Ordine delle chiamate interne eseguite da '{master_func}':")
        for i, nome_funzione in enumerate(chiamate_interne, 1):
            print(f"  {i}. {nome_funzione}()")
    else:
        print(f"La funzione '{master_func}' non chiama altre funzioni interne.")

    # === C. FUNZIONI ORFANE ===
    print("\n=== C. FUNZIONI ORFANE ===")

    # Raccoglie tutte le funzioni che vengono chiamate da ALMENO una funzione nel file
    tutte_le_chiamate_effettuate = set()
    for chiamante, chiamate in analyzer.calls.items():
        for f in chiamate:
            tutte_le_chiamate_effettuate.add(f)

    # Una funzione è orfana se:
    # 1. Non è la funzione master stessa
    # 2. Non compare mai tra le chiamate effettuate da nessuna funzione del file
    funzioni_orfane = [
        func
        for func in analyzer.functions
        if func != master_func and func not in tutte_le_chiamate_effettuate
    ]

    if funzioni_orfane:
        print("Le seguenti funzioni non vengono mai chiamate all'interno del file:")
        for func in funzioni_orfane:
            print(f" - {func}()")
    else:
        print("Nessuna funzione orfana trovata. Tutte le funzioni vengono utilizzate.")

# --- ESEMPIO DI UTILIZZO ---
if __name__ == "__main__":
    # Sostituisci 'views.py' con il percorso del tuo file views di Django
    # Puoi anche specificare un nome diverso se la funzione master si chiama diversamente
    analizza_views("emails/views.py", master_func="process_emails")
