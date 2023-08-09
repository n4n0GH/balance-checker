import os
import csv
import locale
from tabulate import tabulate


# generic function to clear the terminal
def clearScreen():
    os.system("cls" if os.name == "nt" else "clear")


# function to select the file to parse from the import directory
def importfile():
    i = 0
    print("Select file to parse:\n")
    fileList = [f for f in os.listdir("import") if os.path.isfile(os.path.join("import", f))]
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
    filepath = os.path.join(os.getcwd(), "import", fileName)
    if not os.path.isfile(filepath):
        print("      File not found")
        exit()
    return filepath


# function to parse the file and generate the balancesheet
def balancesheet():
    clearScreen()
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
    fname = input("\nExport filename (without extension):\n> ")
    print("\nParsing file...\n")
    # etherscan exports with english decimal separator
    locale.setlocale(locale.LC_ALL, 'en_US')
    with open(filepath, "r") as f:
        dialect = csv.Sniffer().sniff(f.read(), delimiters=",;| ")
        f.seek(0)
        balancereader = csv.DictReader(f, dialect=dialect)
        if "Value_IN(ETH)" in balancereader.fieldnames:
            mode = "eth"
        else:
            mode = "erc20"
        dates = []
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
                valuein = locale.atof(row["Value_IN(ETH)"])
                valueout = locale.atof(row["Value_OUT(ETH)"])
            else:
                token = row["TokenSymbol"]
                valuein = locale.atof(row["TokenValue"])
                valueout = locale.atof(row["TokenValue"])
            if token not in tokens:
                tokens[token] = {}
            if year not in tokens[token]:
                tokens[token][year] = {}
                if "in" not in tokens[token][year]:
                    tokens[token][year]["in"] = float("0")
                if "out" not in tokens[token][year]:
                    tokens[token][year]["out"] = float("0")
            if incoming:
                tokens[token][year]["in"] += valuein
            else:
                tokens[token][year]["out"] -= valueout
        dates.sort()
        for year in dates:
            exportheader.extend((year + " In", year + " Out", year + " Flow"))
    total = {}
    headerextend = []
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
    else:
        suffix = "_erc20.csv"
    with open(os.path.join("export", fname + suffix), "w", encoding="UTF-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(exportheader)
        writer.writerows(table)
    print(tabulate(table, headers=exportheader))


# rerun the script or quit
def cta():
    print("\nAll done. Press Q to quit or any other key to parse another file.")
    userAction = input("> ").strip().lower()
    if userAction == "q":
        exit()
    else:
        init()


# begin program
def init():
    balancesheet()
    cta()


# only run program if executed directly
if __name__ == "__main__":
    init()