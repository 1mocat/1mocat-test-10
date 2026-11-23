#!/usr/bin/env python3
"""
Re-implementation of the COBOL BOOKFORUM program.
Reads INPUT.DAT and updates ACCOUNTS.DAT, BOOKS.DAT, TRANSACTIONS.DAT
exactly as the original COBOL does.
"""

import os

# Record lengths based on COBOL PIC clauses
ACCOUNT_REC_LEN = 4 + 20 + 10  # 34
BOOK_REC_LEN = 4 + 20 + 4      # 28
TRANS_REC_LEN = 4 + 10 + 4 + 4 # 22
INPUT_REC_LEN = 4 + 4 + 4 + 10 # 22

def pad_record(data, length):
    """Pad data to exact length with spaces if short, or truncate if long."""
    if len(data) < length:
        return data + b' ' * (length - len(data))
    return data[:length]

def read_records(path, rec_len):
    """Read sequential fixed-length records from a .DAT file."""
    if not os.path.exists(path):
        return []
    with open(path, 'rb') as f:
        data = f.read()
    # Ensure complete records; pad last if necessary (COBOL style)
    if len(data) % rec_len != 0:
        data += b' ' * (rec_len - (len(data) % rec_len))
    return [data[i:i+rec_len] for i in range(0, len(data), rec_len)]

def write_records(path, records):
    """Write records back as concatenated fixed-length bytes, no newlines."""
    with open(path, 'wb') as f:
        for rec in records:
            f.write(rec)

def parse_input(input_path):
    """Parse the single input record. Handles short files by padding."""
    records = read_records(input_path, INPUT_REC_LEN)
    if not records:
        print("Error: Input file is empty")
        return None
    rec = records[0]
    buyer_id = rec[0:4].decode('ascii', errors='replace').strip()
    seller_id = rec[4:8].decode('ascii', errors='replace').strip()
    book_id = rec[8:12].decode('ascii', errors='replace').strip()
    amount_str = rec[12:22].decode('ascii', errors='replace').strip()
    # COBOL treats the numeric field with trailing spaces as the integer value
    try:
        amount = int(amount_str) if amount_str else 0
    except ValueError:
        amount = 0
    return buyer_id, seller_id, book_id, amount

def main():
    # Paths relative to cobol/ directory (as COBOL is designed to be run from there)
    base_dir = os.path.dirname(os.path.abspath(__file__))
    input_path = os.path.join(base_dir, "src", "INPUT.DAT")
    accounts_path = os.path.join(base_dir, "data", "ACCOUNTS.DAT")
    books_path = os.path.join(base_dir, "data", "BOOKS.DAT")
    trans_path = os.path.join(base_dir, "data", "TRANSACTIONS.DAT")

    parsed = parse_input(input_path)
    if parsed is None:
        return
    buyer_id, seller_id, book_id, amount = parsed

    # VALIDATE-USERS-AND-BOOK
    accounts = read_records(accounts_path, ACCOUNT_REC_LEN)
    books = read_records(books_path, BOOK_REC_LEN)

    buyer_found = False
    seller_found = False
    book_found = False
    valid_owner = False

    for acc in accounts:
        acc_id = acc[0:4].decode('ascii', errors='replace').strip()
        if acc_id == buyer_id:
            buyer_found = True
        if acc_id == seller_id:
            seller_found = True

    for book in books:
        b_id = book[0:4].decode('ascii', errors='replace').strip()
        owner = book[24:28].decode('ascii', errors='replace').strip()
        if b_id == book_id:
            book_found = True
            if owner == seller_id:
                valid_owner = True

    print(" ")  # matches the DISPLAY " " in COBOL

    if buyer_found and seller_found and book_found and valid_owner:
        # PROCESS-TRANSACTION
        # Update accounts
        new_accounts = []
        for acc in accounts:
            acc_id = acc[0:4].decode('ascii', errors='replace').strip()
            name = acc[4:24]
            bal_str = acc[24:34].decode('ascii', errors='replace')
            try:
                balance = int(bal_str)
            except ValueError:
                balance = 0
            if acc_id == buyer_id:
                balance -= amount
            if acc_id == seller_id:
                balance += amount
            # Ensure non-negative? COBOL PIC 9 doesn't go negative typically, but allow
            # Format back to 10 digits zero-padded
            new_bal = f"{balance:010d}".encode('ascii')[:10]
            new_acc = acc[0:4] + name + new_bal
            new_accounts.append(pad_record(new_acc, ACCOUNT_REC_LEN))
        write_records(accounts_path, new_accounts)

        # Update books: change owner of matching book
        new_books = []
        for book in books:
            b_id = book[0:4].decode('ascii', errors='replace').strip()
            title = book[4:24]
            if b_id == book_id:
                new_owner = buyer_id.encode('ascii').ljust(4)[:4]
                new_book = book[0:24] + new_owner
            else:
                new_book = book
            new_books.append(pad_record(new_book, BOOK_REC_LEN))
        write_records(books_path, new_books)

        # Append transaction
        # TRANS: BOOK(4) + AMOUNT(10) + SELLER(4) + BUYER(4)
        trans_amount = f"{amount:010d}".encode('ascii')[:10]
        trans_rec = (
            book_id.encode('ascii').ljust(4)[:4] +
            trans_amount +
            seller_id.encode('ascii').ljust(4)[:4] +
            buyer_id.encode('ascii').ljust(4)[:4]
        )
        trans_rec = pad_record(trans_rec, TRANS_REC_LEN)
        # EXTEND: append
        with open(trans_path, 'ab') as f:
            f.write(trans_rec)

        print("Transaction completed successfully")
    else:
        print("Transaction failed due to validation errors")

if __name__ == "__main__":
    main()
