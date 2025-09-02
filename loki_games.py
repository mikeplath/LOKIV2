#!/usr/bin/env python3
"""
LOKI Games - A collection of text-based mini-games.
Converted from the C++ source provided by mikeplath.
"""

import os
import random
import time
import sys
from abc import ABC, abstractmethod
from datetime import datetime

# --- Utility Functions (from Utils.cpp) ---

class Color:
    """ANSI color codes for terminal output."""
    RESET = "\033[0m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"
    BRIGHT_RED = "\033[91m"
    BRIGHT_GREEN = "\033[92m"
    BRIGHT_YELLOW = "\033[93m"
    BRIGHT_BLUE = "\033[94m"
    BRIGHT_MAGENTA = "\033[95m"
    BRIGHT_CYAN = "\033[96m"

def clear_screen():
    """Clears the terminal screen."""
    os.system('cls' if os.name == 'nt' else 'clear')

def delay(milliseconds):
    """Pauses execution for a number of milliseconds."""
    time.sleep(milliseconds / 1000.0)

def display_title(title):
    """Displays a formatted title."""
    clear_screen()
    print(f"{Color.CYAN}===== {title.upper()} ====={Color.RESET}\n")

def get_valid_input(prompt, min_val, max_val):
    """Gets and validates integer input from the user."""
    while True:
        try:
            choice = int(input(prompt))
            if min_val <= choice <= max_val:
                return choice
            else:
                print(f"{Color.RED}Error: Please enter a number between {min_val} and {max_val}.{Color.RESET}")
        except ValueError:
            print(f"{Color.RED}Error: Invalid input. Please enter a number.{Color.RESET}")

def get_yes_no_response(prompt):
    """Gets a 'y' or 'n' response from the user."""
    while True:
        response = input(prompt).lower()
        if response in ['y', 'n']:
            return response == 'y'
        print(f"{Color.RED}Invalid input. Please enter 'y' or 'n'.{Color.RESET}")

# --- Base Game Class (from Game.h) ---

class Game(ABC):
    """Abstract base class for all games."""
    def __init__(self, name):
        self.name = name
        self.score = 0

    @abstractmethod
    def play(self):
        """The main method to run the game logic."""
        pass
    
    def display_info(self, additional_info=""):
        print(f"\n{Color.CYAN}--- {self.name} Stats ---{Color.RESET}")
        print(f"Total Score: {self.score}")
        if additional_info:
            print(additional_info)
        print(f"{Color.CYAN}-------------------------{Color.RESET}\n")


# --- Rock Paper Scissors (from RockPaperScissors.h/cpp) ---

class RockPaperScissors(Game):
    def __init__(self):
        super().__init__("ROCK PAPER SCISSORS")
        self.ROUNDS_TO_WIN = 3

    def display_rps(self, choice):
        art = {
            1: "    _______\n---'   ____)\n      (_____)\n      (_____)\n      (____)\n---.__(___)\n",
            2: "    _______\n---'   ____)____\n          ______)\n          _______)\n         _______)\n---.__________)\n",
            3: "    _______\n---'   ____)____\n          ______)\n       __________)\n      (____)\n---.__(___)\n"
        }
        print(art.get(choice, "Invalid choice"))

    def play_round(self):
        user_wins = 0
        computer_wins = 0
        display_title(self.name)
        print(f"First to {self.ROUNDS_TO_WIN} wins!\n")

        while user_wins < self.ROUNDS_TO_WIN and computer_wins < self.ROUNDS_TO_WIN:
            print("------------------------------")
            print(f"SCORE: You: {user_wins} | Computer: {computer_wins}")
            print("------------------------------\n")
            
            user_choice = get_valid_input("Choose:\n1: Rock\n2: Paper\n3: Scissors\nEnter your choice (1-3): ", 1, 3)
            
            print("\nYou chose:")
            self.display_rps(user_choice)
            print("VS.\n")
            delay(1000)

            computer_choice = random.randint(1, 3)
            print("Computer chose:")
            self.display_rps(computer_choice)

            if user_choice == computer_choice:
                print(f"{Color.YELLOW}It's a tie! No points awarded.{Color.RESET}")
            elif (user_choice == 1 and computer_choice == 3) or \
                 (user_choice == 2 and computer_choice == 1) or \
                 (user_choice == 3 and computer_choice == 2):
                print(f"{Color.GREEN}You win this round!{Color.RESET}")
                user_wins += 1
            else:
                print(f"{Color.RED}Computer wins this round!{Color.RESET}")
                computer_wins += 1
            
            delay(2000)
            display_title(self.name)
        
        round_score = 0
        if user_wins > computer_wins:
            print(f"{Color.BRIGHT_GREEN}CONGRATULATIONS! YOU WON!{Color.RESET}")
            round_score = 100
        else:
            print(f"{Color.BRIGHT_RED}GAME OVER! COMPUTER WINS!{Color.RESET}")
            round_score = 25
        
        self.score += round_score
    
    def play(self):
        while True:
            self.play_round()
            self.display_info()
            if not get_yes_no_response("Do you want to play Rock-Paper-Scissors again? (y/n): "):
                break

# --- Hangman (from Hangman.h/cpp) ---

class Hangman(Game):
    def __init__(self):
        super().__init__("HANGMAN")
        self.word_list = [
            {"word": "flamingo", "hint": "A pink wading bird that stands on one leg"},
            {"word": "avocado", "hint": "A green fruit with a large pit and creamy texture"},
            {"word": "medieval", "hint": "Relating to the Middle Ages in Europe"},
            {"word": "pterodactyl", "hint": "A prehistoric flying reptile"},
            {"word": "quokka", "hint": "A small marsupial from Australia"},
            {"word": "xylophone", "hint": "A musical instrument with wooden bars"},
            {"word": "zebra", "hint": "A black and white striped animal from Africa"}
        ]

    def display_hangman(self, wrong_guesses):
        stages = [
            "  _____\n |     |\n |      \n |    \n |     \n |      \n |_____\n",
            "  _____\n |     |\n |     O\n |    \n |     \n |      \n |_____\n",
            "  _____\n |     |\n |     O\n |    /\n |     \n |      \n |_____\n",
            "  _____\n |     |\n |     O\n |    /|\n |     \n |      \n |_____\n",
            "  _____\n |     |\n |     O\n |    /|\\\n |     \n |      \n |_____\n",
            "  _____\n |     |\n |     O\n |    /|\\\n |     |\n |      \n |_____\n",
            "  _____\n |     |\n |     O\n |    /|\\\n |     |\n |    / \n |_____\n",
            "  _____\n |     |\n |     O\n |    /|\\\n |     |\n |    / \\\n |_____\n"
        ]
        print(f"{Color.YELLOW}{stages[wrong_guesses]}{Color.RESET}")

    def play_round(self):
        display_title(self.name)
        word_hint = random.choice(self.word_list)
        word = word_hint["word"].lower()
        hint = word_hint["hint"]
        guessed_word = ['_'] * len(word)
        wrong_letters = []
        wrong_count = 0
        max_wrong = 7
        hint_shown = False

        while wrong_count < max_wrong and "".join(guessed_word) != word:
            print("Current word: " + " ".join(guessed_word))
            self.display_hangman(wrong_count)

            if wrong_count >= 4 and not hint_shown:
                print(f"{Color.BRIGHT_CYAN}HINT: {hint}{Color.RESET}")
                hint_shown = True

            print("Wrong guesses: " + " ".join(wrong_letters))
            
            guess = input("Enter a letter: ").lower()

            if len(guess) != 1 or not guess.isalpha():
                print(f"{Color.RED}Invalid input. Please enter a single letter.{Color.RESET}")
            elif guess in wrong_letters or guess in guessed_word:
                print(f"{Color.RED}You already guessed that letter.{Color.RESET}")
            elif guess in word:
                print(f"{Color.GREEN}Good guess!{Color.RESET}")
                for i, letter in enumerate(word):
                    if letter == guess:
                        guessed_word[i] = guess
            else:
                print(f"{Color.RED}Wrong guess!{Color.RESET}")
                wrong_letters.append(guess)
                wrong_count += 1
            
            delay(1000)
            display_title(self.name)

        self.display_hangman(wrong_count)
        round_score = 0
        if "".join(guessed_word) == word:
            print(f"{Color.BRIGHT_GREEN}Congratulations! You guessed the word: {word}{Color.RESET}")
            round_score = 100 - (wrong_count * 10)
        else:
            print(f"{Color.BRIGHT_RED}You lost! The word was: {word}{Color.RESET}")
        
        self.score += round_score

    def play(self):
        while True:
            self.play_round()
            self.display_info("Fewer mistakes = higher score!")
            if not get_yes_no_response("Do you want to play Hangman again? (y/n): "):
                break

# --- Connect 4 (from Connect4.h/cpp) ---

class Connect4(Game):
    def __init__(self):
        super().__init__("CONNECT 4")
        self.ROWS = 6
        self.COLS = 7
        self.PLAYER = 'X'
        self.COMPUTER = 'O'
        self.EMPTY = ' '
        self.board = []

    def new_board(self):
        self.board = [[self.EMPTY for _ in range(self.COLS)] for _ in range(self.ROWS)]

    def print_board(self):
        print("\n " + "   ".join(str(i + 1) for i in range(self.COLS)))
        for r in range(self.ROWS):
            row_str = "| "
            for c in range(self.COLS):
                char = self.board[r][c]
                if char == self.PLAYER:
                    row_str += f"{Color.RED}{char}{Color.RESET} | "
                elif char == self.COMPUTER:
                    row_str += f"{Color.BLUE}{char}{Color.RESET} | "
                else:
                    row_str += f"{char} | "
            print(row_str)
        print("-" * (self.COLS * 4 + 1))

    def is_valid_location(self, col):
        return self.board[0][col] == self.EMPTY

    def get_next_open_row(self, col):
        for r in range(self.ROWS - 1, -1, -1):
            if self.board[r][col] == self.EMPTY:
                return r
        return -1

    def drop_piece(self, row, col, piece):
        self.board[row][col] = piece

    def winning_move(self, piece):
        # Horizontal, Vertical, and Diagonal checks
        for c in range(self.COLS - 3):
            for r in range(self.ROWS):
                if all(self.board[r][c+i] == piece for i in range(4)): return True
        for c in range(self.COLS):
            for r in range(self.ROWS - 3):
                if all(self.board[r+i][c] == piece for i in range(4)): return True
        for c in range(self.COLS - 3):
            for r in range(self.ROWS - 3):
                if all(self.board[r+i][c+i] == piece for i in range(4)): return True
        for c in range(self.COLS - 3):
            for r in range(3, self.ROWS):
                if all(self.board[r-i][c+i] == piece for i in range(4)): return True
        return False

    def get_computer_move(self):
        # Check if computer can win
        for col in range(self.COLS):
            if self.is_valid_location(col):
                row = self.get_next_open_row(col)
                self.board[row][col] = self.COMPUTER
                if self.winning_move(self.COMPUTER):
                    self.board[row][col] = self.EMPTY
                    return col
                self.board[row][col] = self.EMPTY
        # Check if player can win and block
        for col in range(self.COLS):
            if self.is_valid_location(col):
                row = self.get_next_open_row(col)
                self.board[row][col] = self.PLAYER
                if self.winning_move(self.PLAYER):
                    self.board[row][col] = self.EMPTY
                    return col
                self.board[row][col] = self.EMPTY
        # Otherwise, pick a random valid column
        valid_cols = [c for c in range(self.COLS) if self.is_valid_location(c)]
        return random.choice(valid_cols) if valid_cols else -1

    def play_round(self):
        self.new_board()
        game_over = False
        turn = random.randint(0, 1) # Player or Computer starts

        while not game_over:
            display_title(self.name)
            self.print_board()

            if turn == 0: # Player's turn
                col = get_valid_input(f"\n{Color.YELLOW}Your turn. Enter column (1-{self.COLS}): {Color.RESET}", 1, self.COLS) - 1
                if self.is_valid_location(col):
                    row = self.get_next_open_row(col)
                    self.drop_piece(row, col, self.PLAYER)
                    if self.winning_move(self.PLAYER):
                        display_title(self.name); self.print_board()
                        print(f"\n{Color.BRIGHT_GREEN}Congratulations! You connected four!{Color.RESET}")
                        self.score += 100
                        game_over = True
                    turn = 1
                else:
                    print(f"{Color.RED}Column is full. Try again.{Color.RESET}"); delay(1000)
            
            else: # Computer's turn
                print(f"\n{Color.CYAN}Computer is thinking...{Color.RESET}"); delay(1000)
                col = self.get_computer_move()
                if col != -1:
                    row = self.get_next_open_row(col)
                    self.drop_piece(row, col, self.COMPUTER)
                    if self.winning_move(self.COMPUTER):
                        display_title(self.name); self.print_board()
                        print(f"\n{Color.BRIGHT_RED}Computer wins! Better luck next time.{Color.RESET}")
                        self.score += 10
                        game_over = True
                    turn = 0
            
            if all(self.board[0][c] != self.EMPTY for c in range(self.COLS)):
                display_title(self.name); self.print_board()
                print(f"\n{Color.BRIGHT_YELLOW}It's a draw! The board is full.{Color.RESET}")
                self.score += 50
                game_over = True
    
    def play(self):
        while True:
            self.play_round()
            self.display_info()
            if not get_yes_no_response("Do you want to play Connect 4 again? (y/n): "):
                break

# --- Game Manager (from GameManager.h/cpp) ---

class GameManager:
    def __init__(self):
        self.games = [Connect4(), Hangman(), RockPaperScissors()]
        self.high_score_file = "high_scores.txt"
        self.load_high_scores()

    def load_high_scores(self):
        if not os.path.exists(self.high_score_file): return
        try:
            with open(self.high_score_file, 'r') as f:
                for line in f:
                    parts = line.strip().split()
                    if len(parts) >= 2:
                        game_name = " ".join(parts[:-1])
                        score = int(parts[-1])
                        for game in self.games:
                            if game.name == game_name:
                                game.score = score
        except Exception as e:
            print(f"{Color.RED}Warning: Could not load high scores: {e}{Color.RESET}")

    def save_high_scores(self):
        try:
            with open(self.high_score_file, 'w') as f:
                for game in self.games:
                    f.write(f"{game.name} {game.score}\n")
        except Exception as e:
            print(f"{Color.RED}Warning: Could not save high scores: {e}{Color.RESET}")

    def show_high_scores(self):
        print(f"\n{Color.BRIGHT_YELLOW}--- HIGH SCORES ---{Color.RESET}")
        for game in self.games:
            print(f"{game.name}: {game.score}")
        print(f"{Color.BRIGHT_YELLOW}-------------------{Color.RESET}\n")
        input("Press Enter to continue...")

    def run(self):
        """Main loop to display menu and launch games."""
        while True:
            clear_screen()
            print(f"{Color.BRIGHT_MAGENTA}============================={Color.RESET}")
            print(f"{Color.BRIGHT_CYAN}  WELCOME TO LOKI GAMES!{Color.RESET}")
            print(f"{Color.BRIGHT_MAGENTA}============================={Color.RESET}\n")
            for i, game in enumerate(self.games):
                print(f"{i + 1}: Play {game.name}")
            print(f"{len(self.games) + 1}: Show High Scores")
            print(f"{len(self.games) + 2}: Exit")
            
            choice = get_valid_input("\nEnter your choice: ", 1, len(self.games) + 2)
            
            if choice == len(self.games) + 2:
                self.save_high_scores()
                print("\nThanks for playing!")
                break
            elif choice == len(self.games) + 1:
                self.show_high_scores()
            else:
                selected_game = self.games[choice - 1]
                selected_game.play()

# --- Main Execution ---

if __name__ == "__main__":
    try:
        # Initialize random seed
        random.seed()
        manager = GameManager()
        manager.run()
    except KeyboardInterrupt:
        print("\n\nExiting game menu. Goodbye!")
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")
    finally:
        # Reset color before exiting
        print(Color.RESET)
