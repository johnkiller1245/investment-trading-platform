class Game2048 {
    constructor(boardSize = 4) {
        this.boardSize = boardSize;
        this.board = [];
        this.score = 0;
        this.gameBoard = document.getElementById('game-board');
        this.scoreDisplay = document.getElementById('score');
        this.initializeBoard();
        this.setupEventListeners();
    }

    initializeBoard() {
        // Create 2D array
        this.board = Array.from({ length: this.boardSize }, 
            () => Array(this.boardSize).fill(0));
        
        // Add initial tiles
        this.addRandomTile();
        this.addRandomTile();
        
        this.renderBoard();
    }

    addRandomTile() {
        const emptyCells = [];
        for (let r = 0; r < this.boardSize; r++) {
            for (let c = 0; c < this.boardSize; c++) {
                if (this.board[r][c] === 0) {
                    emptyCells.push({ r, c });
                }
            }
        }

        if (emptyCells.length > 0) {
            const { r, c } = emptyCells[Math.floor(Math.random() * emptyCells.length)];
            // 90% chance of 2, 10% chance of 4
            this.board[r][c] = Math.random() < 0.9 ? 2 : 4;
        }
    }

    renderBoard() {
        // Clear existing board
        this.gameBoard.innerHTML = '';
        
        // Create tiles
        for (let r = 0; r < this.boardSize; r++) {
            for (let c = 0; c < this.boardSize; c++) {
                const tileValue = this.board[r][c];
                const tileElement = document.createElement('div');
                tileElement.classList.add('tile');
                
                if (tileValue !== 0) {
                    tileElement.textContent = tileValue;
                    tileElement.classList.add(`tile-${tileValue}`);
                }
                
                this.gameBoard.appendChild(tileElement);
            }
        }
        
        // Update score
        this.scoreDisplay.textContent = this.score;
    }

    move(direction) {
        let moved = false;
        
        const rotateBoard = () => {
            const newBoard = [];
            for (let c = 0; c < this.boardSize; c++) {
                const newRow = [];
                for (let r = this.boardSize - 1; r >= 0; r--) {
                    newRow.push(this.board[r][c]);
                }
                newBoard.push(newRow);
            }
            this.board = newBoard;
        };

        // Normalize direction to always slide left
        switch(direction) {
            case 'ArrowRight':
                this.board = this.board.map(row => row.reverse());
                break;
            case 'ArrowUp':
                rotateBoard();
                break;
            case 'ArrowDown':
                rotateBoard();
                this.board = this.board.map(row => row.reverse());
                break;
        }

        // Slide and merge tiles
        const newBoard = this.board.map(row => {
            // Remove zeros
            row = row.filter(val => val !== 0);
            
            // Merge adjacent equal tiles
            for (let i = 0; i < row.length - 1; i++) {
                if (row[i] === row[i+1]) {
                    row[i] *= 2;
                    this.score += row[i];
                    row.splice(i+1, 1);
                    moved = true;
                }
            }
            
            // Pad with zeros
            while (row.length < this.boardSize) {
                row.push(0);
            }
            
            return row;
        });

        // Restore original board orientation
        switch(direction) {
            case 'ArrowRight':
                this.board = newBoard.map(row => row.reverse());
                break;
            case 'ArrowUp':
                // Rotate back
                const rotatedBack = [];
                for (let c = 0; c < this.boardSize; c++) {
                    const newRow = [];
                    for (let r = 0; r < this.boardSize; r++) {
                        newRow.push(newBoard[r][c]);
                    }
                    rotatedBack.push(newRow);
                }
                this.board = rotatedBack;
                break;
            case 'ArrowDown':
                // Rotate and reverse
                const rotatedAndReversed = [];
                for (let c = 0; c < this.boardSize; c++) {
                    const newRow = [];
                    for (let r = this.boardSize - 1; r >= 0; r--) {
                        newRow.push(newBoard[r][c]);
                    }
                    rotatedAndReversed.push(newRow);
                }
                this.board = rotatedAndReversed;
                break;
            default:
                this.board = newBoard;
        }

        // Add new tile if board changed
        if (moved) {
            this.addRandomTile();
        }

        this.renderBoard();
        this.checkGameStatus();
    }

    checkGameStatus() {
        // Check for 2048
        for (let r = 0; r < this.boardSize; r++) {
            for (let c = 0; c < this.boardSize; c++) {
                if (this.board[r][c] === 2048) {
                    alert('Congratulations! You reached 2048!');
                    return;
                }
            }
        }

        // Check if game is over (no moves possible)
        const isBoardFull = this.board.every(row => row.every(cell => cell !== 0));
        const noMergesPossible = !this.canMerge();

        if (isBoardFull && noMergesPossible) {
            alert('Game Over! No more moves possible.');
        }
    }

    canMerge() {
        // Check if any adjacent tiles can be merged
        for (let r = 0; r < this.boardSize; r++) {
            for (let c = 0; c < this.boardSize; c++) {
                // Check right
                if (c < this.boardSize - 1 && 
                    this.board[r][c] === this.board[r][c+1]) {
                    return true;
                }
                // Check down
                if (r < this.boardSize - 1 && 
                    this.board[r][c] === this.board[r+1][c]) {
                    return true;
                }
            }
        }
        return false;
    }

    setupEventListeners() {
        // Keyboard controls
        document.addEventListener('keydown', (e) => {
            if (['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'].includes(e.key)) {
                e.preventDefault();
                this.move(e.key);
            }
        });

        // Touch controls (basic implementation)
        let touchStartX = 0;
        let touchStartY = 0;

        this.gameBoard.addEventListener('touchstart', (e) => {
            touchStartX = e.touches[0].clientX;
            touchStartY = e.touches[0].clientY;
        });

        this.gameBoard.addEventListener('touchend', (e) => {
            const touchEndX = e.changedTouches[0].clientX;
            const touchEndY = e.changedTouches[0].clientY;

            const diffX = touchEndX - touchStartX;
            const diffY = touchEndY - touchStartY;

            // Determine swipe direction
            if (Math.abs(diffX) > Math.abs(diffY)) {
                // Horizontal swipe
                if (diffX > 0) {
                    this.move('ArrowRight');
                } else {
                    this.move('ArrowLeft');
                }
            } else {
                // Vertical swipe
                if (diffY > 0) {
                    this.move('ArrowDown');
                } else {
                    this.move('ArrowUp');
                }
            }
        });
    }
}

// Initialize the game when the page loads
document.addEventListener('DOMContentLoaded', () => {
    new Game2048();
});
