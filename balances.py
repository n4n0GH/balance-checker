import os
import csv
from tabulate import tabulate
import decimal


# generic function to clear the terminal
def clearScreen():
    os.system("cls" if os.name == "nt" else "clear")


# convert string to decimal with precision
def decimalize(v):
    return decimal.Decimal(v.replace(',', '')).quantize(decimal.Decimal(f"0.{'0' * 18}"))


# function to select the file to parse from the import directory
def importfile(dir="import"):
    i = 0
    print("Select file to parse:\n")
    fileList = [f for f in os.listdir(dir) if os.path.isfile(os.path.join(dir, f))]
    if len(fileList) == 0:
        print("No files found in import folder. Please add a file and try again.")
        print("Use https://etherscan.io/exportData to generate the CSV file.")
        exit()
    for singleFile in fileList:
        i += 1
        spacer = (5 - len(str(i))) * " "
        print(str(i) + spacer + singleFile)
    print("\n")
    fileSelection = input("> ").strip()
    fileName = ""
    try:
        selection = int(fileSelection) - 1
        if selection <= len(fileList):
            fileName = fileList[selection]
    except:
        raise
    filepath = os.path.join(os.getcwd(), dir, fileName)
    if not os.path.isfile(filepath):
        print("      File not found")
        exit()
    return filepath


# function to parse the file and generate the balancesheet
def balancesheet():
    clearScreen()
    weth = "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2"
    table = []
    exportheader = ["Token"]
    tokens = {}
    mode = ""
    suffix = ""
    filepath = importfile()
    owner = input("Focus on wallet:\n> ")
    if len(owner) < 42:
        print("The wallet address you entered is not valid.")
        exit()
    print("\nParsing file...\n")
    with open(filepath, "r") as f:
        dialect = csv.Sniffer().sniff(f.read(), delimiters=",;| ")
        f.seek(0)
        balancereader = csv.DictReader(f, dialect=dialect)
        if "Value_IN(ETH)" in balancereader.fieldnames and "TxTo" not in balancereader.fieldnames:
            mode = "eth"
        elif "TxTo" in balancereader.fieldnames:
            mode = "eth_internal"
        elif "Quantity" in balancereader.fieldnames:
            mode = "erc20_specific"
            symbol = input("Token symbol:\n> ").strip().upper()
        else:
            mode = "erc20"
        dates = []
        def processdata(token, year, valuein, valueout, incoming):
            if token not in tokens:
                tokens[token] = {}
            if year not in tokens[token]:
                tokens[token][year] = {}
                if "in" not in tokens[token][year]:
                    tokens[token][year]["in"] = decimalize("0")
                if "out" not in tokens[token][year]:
                    tokens[token][year]["out"] = decimalize("0")
            if incoming:
                tokens[token][year]["in"] += valuein
            else:
                tokens[token][year]["out"] -= valueout
        for row in balancereader:
            if row["From"].lower() == owner.lower():
                incoming = False
            else:
                incoming = True
            year = int(row["DateTime (UTC)"][0:4])
            if str(year) not in dates:
                dates.append(str(year))
            # etherscan exports for transactions and token transfers are different
            if mode == "eth":
                token = "ETH"
                if row["Status"] == "":
                    valuein = decimalize(row["Value_IN(ETH)"])
                    valueout = decimalize(row["Value_OUT(ETH)"]) + decimalize(row["TxnFee(ETH)"])
                else:
                    valuein = decimalize("0")
                    valueout = decimalize(row["TxnFee(ETH)"])
            if mode == "eth_internal":
                token = "ETH"
                if row["Status"] == "0":
                    valuein = decimalize(row["Value_IN(ETH)"])
                else:
                    valuein = decimalize("0")
                valueout = decimalize(row["Value_OUT(ETH)"])
            if mode == "erc20_specific":
                token = symbol
                valuein = decimalize(row["Quantity"])
                valueout = decimalize(row["Quantity"])
            if mode == "erc20":
                token = row["TokenSymbol"]
                valuein = decimalize(row["TokenValue"])
                valueout = decimalize(row["TokenValue"])
            processdata(token, year, valuein, valueout, incoming)
            if mode == "eth": 
                if row["To"].lower() == weth and row["Method"] == "Deposit":
                    processdata("WETH", year, decimalize(row["Value_OUT(ETH)"]), decimalize(row["Value_OUT(ETH)"]), True)
        dates.sort()
        for year in dates:
            exportheader.extend((year + " In", year + " Out", year + " Flow"))
    total = {}
    for name, data in sorted(tokens.items(), key=lambda x: x[0].casefold()):
        balances = [name]
        for year in dates:
            # some tokens might not have any transactions in a given year so we need to add dummy data
            if int(year) not in data.keys():
                data[int(year)] = {"in": 0, "out": 0}
        for year, value in sorted(data.items()):
            balances.extend([f'{value["in"]:.18f}', f'{value["out"]:.18f}', f'{value["in"] + value["out"]:.18f}'])
            if name not in total:
                total[name] = 0
            total[name] += value["in"] + value["out"]
        balances.append(f'{total[name]:.18f}')
        table.extend([balances])
    exportheader.append("Balance")
    if mode == "eth":
        suffix = "_eth.csv"
    elif mode == "eth_internal":
        suffix = "_eth_internal.csv"
    elif mode == "erc20_specific":
        suffix = "_" + symbol + ".csv"
    else:
        suffix = "_erc20.csv"
    with open(os.path.join("export", owner + suffix), "w", encoding="UTF-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(exportheader)
        writer.writerows(table)
    clearScreen()
    print(tabulate(table, headers=exportheader))
    cta()


# parse and merge multiple files
def merge():
    clearScreen()
    files = []
    header = []
    tokens = []
    owner = input("Focus on wallet:\n> ")
    if len(owner) < 42:
        print("The wallet address you entered is not valid.")
        exit()
    def selection():
        clearScreen()
        print("\nSelected files to merge: ", files)
        files.append(importfile("export"))
        print("\nPress M to begin merging or any other key to parse another file.")
        userAction = input("> ").strip().lower()
        if userAction != "m":
            selection()
        if len(files) < 2:
            selection()
    selection()
    for file in files:
        with open(file, "r") as f:
            dialect = csv.Sniffer().sniff(f.read(), delimiters=",;| ")
            f.seek(0)
            reader = csv.DictReader(f, dialect=dialect)
            if len(header) == 0:
                header = reader.fieldnames
            for row in reader:
                if not any(row["Token"] in sl for sl in tokens):
                    data = []
                    for v in row.values():
                        data.append(v)
                    tokens.append(data)
                else:
                    for token in tokens:
                        if token[0] == row["Token"]:
                            for i in range(1, len(header)):
                                token[i] = decimalize(token[i]) + decimalize(row[header[i]])
    with open(os.path.join("export", owner + "_merged.csv"), "w", encoding="UTF-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(tokens)
    clearScreen()
    print(tabulate(tokens, headers=header))
    cta()

# select script mode
def cta():
    print("\n[P]arse etherscan files | [M]erge parsed files | [Q]uit")
    userAction = input("> ").strip().lower()
    if userAction == "q":
        exit()
    elif userAction == "m":
        merge()
    elif userAction == "p":
        init()
    else:
        cta()


# create directories if they don't exist
def directorysetup():
    try:
        os.makedirs("import", exist_ok=True)
        os.makedirs("export", exist_ok=True)
    except OSError:
        print("Creation of the directories failed")
        exit()


# begin program
def init():
    directorysetup()
    balancesheet()


# only run program if executed directly
if __name__ == "__main__":
    cta()