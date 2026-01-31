"""
Seed script for Lab Assistance tables
Adds comprehensive B.Tech lab data for all branches
"""

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta
import uuid
import json

# Database connection
sync_url = 'postgresql://bharatbuild:password@localhost:5432/bharatbuild_db'
engine = create_engine(sync_url)
Session = sessionmaker(bind=engine)
session = Session()

def generate_uuid():
    return str(uuid.uuid4())

# ============================================================================
# LABS DATA
# ============================================================================

labs_data = [
    # CSE Labs
    {
        "name": "C Programming Lab",
        "code": "CSE-101-LAB",
        "description": "Fundamentals of C programming including data types, control structures, functions, arrays, pointers, and file handling.",
        "branch": "CSE",
        "semester": "SEM_1",
        "technologies": ["C", "GCC", "Linux"],
    },
    {
        "name": "Data Structures Lab",
        "code": "CSE-201-LAB",
        "description": "Implementation of fundamental data structures: arrays, linked lists, stacks, queues, trees, and graphs.",
        "branch": "CSE",
        "semester": "SEM_3",
        "technologies": ["C", "C++", "Python"],
    },
    {
        "name": "Database Management Systems Lab",
        "code": "CSE-301-LAB",
        "description": "SQL queries, database design, normalization, PL/SQL programming, and transaction management.",
        "branch": "CSE",
        "semester": "SEM_4",
        "technologies": ["SQL", "MySQL", "PostgreSQL", "Oracle"],
    },
    {
        "name": "Operating Systems Lab",
        "code": "CSE-302-LAB",
        "description": "Process scheduling, memory management, file systems, and shell scripting.",
        "branch": "CSE",
        "semester": "SEM_4",
        "technologies": ["C", "Linux", "Shell"],
    },
    {
        "name": "Computer Networks Lab",
        "code": "CSE-401-LAB",
        "description": "Socket programming, network protocols, packet analysis, and network configuration.",
        "branch": "CSE",
        "semester": "SEM_5",
        "technologies": ["Python", "C", "Wireshark", "Socket Programming"],
    },
    {
        "name": "Web Technologies Lab",
        "code": "CSE-402-LAB",
        "description": "HTML, CSS, JavaScript, PHP, and full-stack web development.",
        "branch": "CSE",
        "semester": "SEM_5",
        "technologies": ["HTML", "CSS", "JavaScript", "PHP", "MySQL"],
    },
    {
        "name": "Machine Learning Lab",
        "code": "CSE-501-LAB",
        "description": "Implementation of ML algorithms: regression, classification, clustering, and neural networks.",
        "branch": "CSE",
        "semester": "SEM_6",
        "technologies": ["Python", "NumPy", "Pandas", "Scikit-learn", "TensorFlow"],
    },
    {
        "name": "Compiler Design Lab",
        "code": "CSE-502-LAB",
        "description": "Lexical analysis, parsing, syntax trees, and code generation.",
        "branch": "CSE",
        "semester": "SEM_6",
        "technologies": ["C", "Lex", "Yacc", "Python"],
    },

    # IT Labs
    {
        "name": "Python Programming Lab",
        "code": "IT-101-LAB",
        "description": "Python fundamentals, OOP, file handling, and libraries.",
        "branch": "IT",
        "semester": "SEM_2",
        "technologies": ["Python", "NumPy", "Matplotlib"],
    },
    {
        "name": "Java Programming Lab",
        "code": "IT-201-LAB",
        "description": "Core Java, OOP concepts, exception handling, collections, and multithreading.",
        "branch": "IT",
        "semester": "SEM_3",
        "technologies": ["Java", "JDK", "Eclipse"],
    },
    {
        "name": "Software Engineering Lab",
        "code": "IT-301-LAB",
        "description": "SDLC models, UML diagrams, testing, and project management.",
        "branch": "IT",
        "semester": "SEM_5",
        "technologies": ["UML", "Git", "JIRA", "Testing Tools"],
    },

    # ECE Labs
    {
        "name": "Digital Electronics Lab",
        "code": "ECE-201-LAB",
        "description": "Logic gates, combinational circuits, sequential circuits, and FPGA programming.",
        "branch": "ECE",
        "semester": "SEM_3",
        "technologies": ["Verilog", "VHDL", "Xilinx", "Logisim"],
    },
    {
        "name": "Microprocessor Lab",
        "code": "ECE-301-LAB",
        "description": "8085/8086 programming, interfacing, and embedded systems basics.",
        "branch": "ECE",
        "semester": "SEM_4",
        "technologies": ["Assembly", "8085", "8086", "Keil"],
    },
    {
        "name": "Embedded Systems Lab",
        "code": "ECE-401-LAB",
        "description": "ARM programming, RTOS, sensor interfacing, and IoT projects.",
        "branch": "ECE",
        "semester": "SEM_6",
        "technologies": ["C", "ARM", "Arduino", "Raspberry Pi"],
    },

    # EEE Labs
    {
        "name": "Basic Electrical Lab",
        "code": "EEE-101-LAB",
        "description": "Circuit analysis, Kirchhoffs laws, and electrical measurements.",
        "branch": "EEE",
        "semester": "SEM_2",
        "technologies": ["MATLAB", "Multisim", "Oscilloscope"],
    },
    {
        "name": "Control Systems Lab",
        "code": "EEE-301-LAB",
        "description": "Transfer functions, stability analysis, and PID controllers.",
        "branch": "EEE",
        "semester": "SEM_5",
        "technologies": ["MATLAB", "Simulink", "LabVIEW"],
    },

    # ME Labs
    {
        "name": "Engineering Drawing Lab",
        "code": "ME-101-LAB",
        "description": "Orthographic projections, isometric views, and CAD basics.",
        "branch": "ME",
        "semester": "SEM_1",
        "technologies": ["AutoCAD", "SolidWorks"],
    },
    {
        "name": "CAD/CAM Lab",
        "code": "ME-401-LAB",
        "description": "3D modeling, CNC programming, and manufacturing simulations.",
        "branch": "ME",
        "semester": "SEM_6",
        "technologies": ["AutoCAD", "SolidWorks", "CATIA", "CNC"],
    },

    # AI/ML Labs
    {
        "name": "Deep Learning Lab",
        "code": "AI-401-LAB",
        "description": "Neural networks, CNNs, RNNs, and deep learning frameworks.",
        "branch": "AI_ML",
        "semester": "SEM_5",
        "technologies": ["Python", "TensorFlow", "PyTorch", "Keras"],
    },
    {
        "name": "Natural Language Processing Lab",
        "code": "AI-501-LAB",
        "description": "Text processing, sentiment analysis, and language models.",
        "branch": "AI_ML",
        "semester": "SEM_6",
        "technologies": ["Python", "NLTK", "SpaCy", "Transformers"],
    },
]

# ============================================================================
# TOPICS DATA (for each lab)
# ============================================================================

def get_topics_for_lab(lab_code):
    topics_map = {
        "CSE-101-LAB": [
            {"title": "Introduction to C Programming", "week": 1, "description": "Setting up environment, first program, compilation process"},
            {"title": "Data Types and Variables", "week": 2, "description": "Primitive data types, variables, constants, and type conversion"},
            {"title": "Operators and Expressions", "week": 3, "description": "Arithmetic, relational, logical, and bitwise operators"},
            {"title": "Control Structures", "week": 4, "description": "If-else, switch-case, loops (for, while, do-while)"},
            {"title": "Functions", "week": 5, "description": "Function declaration, definition, call by value/reference, recursion"},
            {"title": "Arrays", "week": 6, "description": "1D and 2D arrays, array operations, searching and sorting"},
            {"title": "Pointers", "week": 7, "description": "Pointer basics, pointer arithmetic, pointers and arrays"},
            {"title": "Strings", "week": 8, "description": "String handling, string functions, string manipulation"},
            {"title": "Structures and Unions", "week": 9, "description": "Structure declaration, nested structures, unions"},
            {"title": "File Handling", "week": 10, "description": "File operations, reading/writing files, binary files"},
        ],
        "CSE-201-LAB": [
            {"title": "Arrays and Time Complexity", "week": 1, "description": "Array operations, Big O notation, complexity analysis"},
            {"title": "Linked Lists - Singly", "week": 2, "description": "Creation, insertion, deletion, traversal of singly linked list"},
            {"title": "Linked Lists - Doubly & Circular", "week": 3, "description": "Doubly linked list, circular linked list operations"},
            {"title": "Stacks", "week": 4, "description": "Stack implementation using arrays and linked lists, applications"},
            {"title": "Queues", "week": 5, "description": "Queue, circular queue, priority queue implementations"},
            {"title": "Binary Trees", "week": 6, "description": "Tree creation, traversals (inorder, preorder, postorder)"},
            {"title": "Binary Search Trees", "week": 7, "description": "BST operations: insert, delete, search, balancing"},
            {"title": "Heaps", "week": 8, "description": "Min heap, max heap, heap sort, priority queue using heap"},
            {"title": "Graphs - Basics", "week": 9, "description": "Graph representation, BFS, DFS traversals"},
            {"title": "Graph Algorithms", "week": 10, "description": "Shortest path (Dijkstra, Floyd), MST (Prim, Kruskal)"},
        ],
        "CSE-301-LAB": [
            {"title": "SQL Basics", "week": 1, "description": "DDL commands: CREATE, ALTER, DROP, database design"},
            {"title": "SQL Queries - SELECT", "week": 2, "description": "SELECT, WHERE, ORDER BY, DISTINCT, LIMIT"},
            {"title": "SQL Joins", "week": 3, "description": "INNER JOIN, LEFT JOIN, RIGHT JOIN, FULL JOIN, self join"},
            {"title": "Aggregate Functions", "week": 4, "description": "COUNT, SUM, AVG, MIN, MAX, GROUP BY, HAVING"},
            {"title": "Subqueries", "week": 5, "description": "Nested queries, correlated subqueries, EXISTS, IN"},
            {"title": "Views and Indexes", "week": 6, "description": "Creating views, index types, query optimization"},
            {"title": "PL/SQL Basics", "week": 7, "description": "Variables, control structures, cursors"},
            {"title": "Stored Procedures", "week": 8, "description": "Creating procedures, functions, parameters"},
            {"title": "Triggers", "week": 9, "description": "BEFORE/AFTER triggers, row-level vs statement-level"},
            {"title": "Transactions", "week": 10, "description": "ACID properties, COMMIT, ROLLBACK, isolation levels"},
        ],
        "CSE-401-LAB": [
            {"title": "Network Basics & Configuration", "week": 1, "description": "IP addressing, subnetting, network configuration"},
            {"title": "Socket Programming - TCP", "week": 2, "description": "TCP client-server programming in Python/C"},
            {"title": "Socket Programming - UDP", "week": 3, "description": "UDP client-server, differences from TCP"},
            {"title": "HTTP Protocol", "week": 4, "description": "HTTP requests, responses, building a simple web server"},
            {"title": "DNS and DHCP", "week": 5, "description": "DNS resolution, DHCP configuration"},
            {"title": "Packet Analysis", "week": 6, "description": "Using Wireshark, analyzing network packets"},
            {"title": "Network Security", "week": 7, "description": "Encryption basics, SSL/TLS, secure communication"},
            {"title": "Routing Protocols", "week": 8, "description": "Static routing, RIP, OSPF basics"},
        ],
        "CSE-501-LAB": [
            {"title": "Python for ML & Data Preprocessing", "week": 1, "description": "NumPy, Pandas, data cleaning, feature scaling"},
            {"title": "Linear Regression", "week": 2, "description": "Simple and multiple linear regression implementation"},
            {"title": "Logistic Regression", "week": 3, "description": "Binary classification, sigmoid function, evaluation metrics"},
            {"title": "Decision Trees", "week": 4, "description": "ID3, C4.5, CART algorithms, pruning"},
            {"title": "Random Forests & Ensemble Methods", "week": 5, "description": "Bagging, boosting, random forest implementation"},
            {"title": "K-Means Clustering", "week": 6, "description": "K-means algorithm, elbow method, silhouette score"},
            {"title": "Support Vector Machines", "week": 7, "description": "SVM for classification, kernel functions"},
            {"title": "Neural Networks Basics", "week": 8, "description": "Perceptron, multilayer networks, backpropagation"},
            {"title": "Deep Learning with TensorFlow", "week": 9, "description": "Building neural networks with TensorFlow/Keras"},
            {"title": "CNN for Image Classification", "week": 10, "description": "Convolutional neural networks, image classification"},
        ],
        "IT-201-LAB": [
            {"title": "Java Basics", "week": 1, "description": "JDK setup, first program, data types, operators"},
            {"title": "Control Statements", "week": 2, "description": "If-else, switch, loops, break, continue"},
            {"title": "OOP - Classes & Objects", "week": 3, "description": "Class definition, objects, constructors, this keyword"},
            {"title": "Inheritance", "week": 4, "description": "Single, multilevel, hierarchical inheritance, super keyword"},
            {"title": "Polymorphism", "week": 5, "description": "Method overloading, overriding, abstract classes"},
            {"title": "Interfaces & Packages", "week": 6, "description": "Interface implementation, creating packages"},
            {"title": "Exception Handling", "week": 7, "description": "Try-catch, finally, throw, throws, custom exceptions"},
            {"title": "Collections Framework", "week": 8, "description": "List, Set, Map interfaces, ArrayList, HashMap"},
            {"title": "Multithreading", "week": 9, "description": "Thread creation, synchronization, thread pools"},
            {"title": "File I/O & Serialization", "week": 10, "description": "File handling, streams, object serialization"},
        ],
        "ECE-201-LAB": [
            {"title": "Logic Gates", "week": 1, "description": "AND, OR, NOT, NAND, NOR, XOR gates implementation"},
            {"title": "Boolean Algebra", "week": 2, "description": "Boolean expressions, simplification, K-maps"},
            {"title": "Combinational Circuits - Adders", "week": 3, "description": "Half adder, full adder, ripple carry adder"},
            {"title": "Multiplexers & Decoders", "week": 4, "description": "MUX, DEMUX, encoder, decoder circuits"},
            {"title": "Flip-Flops", "week": 5, "description": "SR, JK, D, T flip-flops, timing diagrams"},
            {"title": "Counters", "week": 6, "description": "Synchronous and asynchronous counters, mod-n counters"},
            {"title": "Shift Registers", "week": 7, "description": "SISO, SIPO, PISO, PIPO registers"},
            {"title": "Verilog Basics", "week": 8, "description": "Verilog syntax, modules, testbenches"},
        ],
        "AI-401-LAB": [
            {"title": "Deep Learning Fundamentals", "week": 1, "description": "Neural network basics, activation functions, loss functions"},
            {"title": "TensorFlow/Keras Basics", "week": 2, "description": "Setting up environment, building first neural network"},
            {"title": "Convolutional Neural Networks", "week": 3, "description": "CNN architecture, convolution, pooling layers"},
            {"title": "Image Classification", "week": 4, "description": "Building CNN for MNIST, CIFAR-10 classification"},
            {"title": "Transfer Learning", "week": 5, "description": "Using pre-trained models (VGG, ResNet, Inception)"},
            {"title": "Recurrent Neural Networks", "week": 6, "description": "RNN basics, vanishing gradient problem"},
            {"title": "LSTM & GRU", "week": 7, "description": "Long Short-Term Memory, Gated Recurrent Units"},
            {"title": "Sequence to Sequence Models", "week": 8, "description": "Encoder-decoder architecture, attention mechanism"},
            {"title": "GANs Introduction", "week": 9, "description": "Generative Adversarial Networks basics"},
            {"title": "Model Deployment", "week": 10, "description": "Saving models, TensorFlow Serving, Flask API"},
        ],
    }
    return topics_map.get(lab_code, [
        {"title": "Introduction", "week": 1, "description": "Course overview and basics"},
        {"title": "Core Concepts", "week": 2, "description": "Fundamental concepts and theory"},
        {"title": "Practical Applications", "week": 3, "description": "Hands-on exercises"},
        {"title": "Advanced Topics", "week": 4, "description": "Advanced concepts and techniques"},
        {"title": "Project Work", "week": 5, "description": "Mini project implementation"},
    ])

# ============================================================================
# MCQ DATA
# ============================================================================

def get_mcqs_for_topic(lab_code, topic_title):
    mcqs_map = {
        ("CSE-101-LAB", "Introduction to C Programming"): [
            {
                "question": "Who developed the C programming language?",
                "options": ["Dennis Ritchie", "James Gosling", "Bjarne Stroustrup", "Guido van Rossum"],
                "correct": 0,
                "explanation": "Dennis Ritchie developed C at Bell Labs in 1972.",
                "difficulty": "EASY"
            },
            {
                "question": "Which of the following is the correct extension of a C source file?",
                "options": [".cpp", ".c", ".java", ".py"],
                "correct": 1,
                "explanation": "C source files use the .c extension.",
                "difficulty": "EASY"
            },
            {
                "question": "What is the output of: printf(\"%d\", sizeof(int));",
                "options": ["2", "4", "8", "Depends on system"],
                "correct": 3,
                "explanation": "The size of int depends on the system architecture (typically 4 bytes on 32/64-bit systems).",
                "difficulty": "MEDIUM"
            },
            {
                "question": "Which header file is required for printf() function?",
                "options": ["stdlib.h", "string.h", "stdio.h", "math.h"],
                "correct": 2,
                "explanation": "stdio.h (Standard Input Output) contains printf() and scanf() functions.",
                "difficulty": "EASY"
            },
            {
                "question": "What does the 'return 0' statement indicate in main()?",
                "options": ["Error occurred", "Successful execution", "Infinite loop", "Memory allocation"],
                "correct": 1,
                "explanation": "return 0 indicates successful program execution to the operating system.",
                "difficulty": "EASY"
            },
        ],
        ("CSE-101-LAB", "Data Types and Variables"): [
            {
                "question": "What is the size of 'char' data type in C?",
                "options": ["1 byte", "2 bytes", "4 bytes", "8 bytes"],
                "correct": 0,
                "explanation": "char always occupies 1 byte (8 bits) in C.",
                "difficulty": "EASY"
            },
            {
                "question": "Which of the following is a valid variable name in C?",
                "options": ["2variable", "variable_2", "variable-2", "variable 2"],
                "correct": 1,
                "explanation": "Variable names can contain letters, digits, and underscores, but cannot start with a digit.",
                "difficulty": "EASY"
            },
            {
                "question": "What is the range of 'unsigned char'?",
                "options": ["-128 to 127", "0 to 255", "-256 to 255", "0 to 127"],
                "correct": 1,
                "explanation": "unsigned char uses all 8 bits for positive values, giving range 0-255.",
                "difficulty": "MEDIUM"
            },
            {
                "question": "Which format specifier is used for double?",
                "options": ["%d", "%f", "%lf", "%ld"],
                "correct": 2,
                "explanation": "%lf is used for double in scanf(), though %f works in printf().",
                "difficulty": "MEDIUM"
            },
        ],
        ("CSE-101-LAB", "Control Structures"): [
            {
                "question": "What is the output of: for(int i=0; i<5; i++); printf(\"%d\", i);",
                "options": ["0", "4", "5", "Compilation error"],
                "correct": 3,
                "explanation": "Variable i is declared inside for loop and not accessible outside (in C99+).",
                "difficulty": "HARD"
            },
            {
                "question": "Which loop is guaranteed to execute at least once?",
                "options": ["for loop", "while loop", "do-while loop", "None of the above"],
                "correct": 2,
                "explanation": "do-while loop checks condition after executing the body, so it runs at least once.",
                "difficulty": "EASY"
            },
            {
                "question": "What does 'break' statement do in a loop?",
                "options": ["Skips current iteration", "Terminates the loop", "Continues to next iteration", "Restarts the loop"],
                "correct": 1,
                "explanation": "break immediately terminates the innermost loop or switch statement.",
                "difficulty": "EASY"
            },
        ],
        ("CSE-101-LAB", "Pointers"): [
            {
                "question": "What is a pointer in C?",
                "options": ["A variable that stores an integer", "A variable that stores a memory address", "A function that points to data", "A keyword in C"],
                "correct": 1,
                "explanation": "A pointer is a variable that stores the memory address of another variable.",
                "difficulty": "EASY"
            },
            {
                "question": "What does the * operator do when used with a pointer?",
                "options": ["Multiplies values", "Dereferences the pointer", "Gets the address", "Declares a pointer"],
                "correct": 1,
                "explanation": "The * operator dereferences a pointer, accessing the value at the stored address.",
                "difficulty": "EASY"
            },
            {
                "question": "What is the output of: int a=5, *p=&a; printf(\"%d\", *p);",
                "options": ["Address of a", "5", "Garbage value", "0"],
                "correct": 1,
                "explanation": "*p dereferences pointer p to get the value of a, which is 5.",
                "difficulty": "MEDIUM"
            },
            {
                "question": "What is a NULL pointer?",
                "options": ["A pointer pointing to 0", "A pointer pointing to nothing", "An uninitialized pointer", "A pointer to empty string"],
                "correct": 1,
                "explanation": "NULL pointer is a pointer that doesn't point to any valid memory location.",
                "difficulty": "EASY"
            },
        ],
        ("CSE-201-LAB", "Arrays and Time Complexity"): [
            {
                "question": "What is the time complexity of accessing an element in an array by index?",
                "options": ["O(1)", "O(n)", "O(log n)", "O(n²)"],
                "correct": 0,
                "explanation": "Array access by index is O(1) as it uses direct memory addressing.",
                "difficulty": "EASY"
            },
            {
                "question": "What is the time complexity of linear search?",
                "options": ["O(1)", "O(n)", "O(log n)", "O(n²)"],
                "correct": 1,
                "explanation": "Linear search checks each element once, so it's O(n).",
                "difficulty": "EASY"
            },
            {
                "question": "What is the space complexity of an algorithm that uses a single array of size n?",
                "options": ["O(1)", "O(n)", "O(log n)", "O(n²)"],
                "correct": 1,
                "explanation": "An array of size n requires O(n) space.",
                "difficulty": "EASY"
            },
        ],
        ("CSE-201-LAB", "Linked Lists - Singly"): [
            {
                "question": "What is the time complexity of inserting at the beginning of a singly linked list?",
                "options": ["O(1)", "O(n)", "O(log n)", "O(n²)"],
                "correct": 0,
                "explanation": "Inserting at the beginning only requires updating the head pointer, which is O(1).",
                "difficulty": "EASY"
            },
            {
                "question": "What is the main advantage of linked list over array?",
                "options": ["Faster access", "Dynamic size", "Less memory", "Better cache performance"],
                "correct": 1,
                "explanation": "Linked lists can grow/shrink dynamically without reallocation.",
                "difficulty": "EASY"
            },
            {
                "question": "How do you detect a cycle in a linked list?",
                "options": ["Using a counter", "Using two pointers (Floyd's algorithm)", "By checking each node", "Not possible"],
                "correct": 1,
                "explanation": "Floyd's cycle detection uses two pointers moving at different speeds.",
                "difficulty": "MEDIUM"
            },
        ],
        ("CSE-201-LAB", "Stacks"): [
            {
                "question": "What principle does a stack follow?",
                "options": ["FIFO", "LIFO", "Random access", "Priority based"],
                "correct": 1,
                "explanation": "Stack follows Last In First Out (LIFO) principle.",
                "difficulty": "EASY"
            },
            {
                "question": "Which operation adds an element to the stack?",
                "options": ["Pop", "Push", "Peek", "Insert"],
                "correct": 1,
                "explanation": "Push operation adds an element to the top of the stack.",
                "difficulty": "EASY"
            },
            {
                "question": "What is a common application of stacks?",
                "options": ["BFS traversal", "Function call management", "Job scheduling", "Page replacement"],
                "correct": 1,
                "explanation": "The call stack manages function calls and returns in programs.",
                "difficulty": "MEDIUM"
            },
        ],
        ("CSE-301-LAB", "SQL Basics"): [
            {
                "question": "Which SQL command is used to create a new table?",
                "options": ["INSERT TABLE", "CREATE TABLE", "NEW TABLE", "ADD TABLE"],
                "correct": 1,
                "explanation": "CREATE TABLE is the DDL command to create a new table.",
                "difficulty": "EASY"
            },
            {
                "question": "Which of the following is a DDL command?",
                "options": ["SELECT", "INSERT", "ALTER", "UPDATE"],
                "correct": 2,
                "explanation": "ALTER is a DDL command that modifies table structure. SELECT, INSERT, UPDATE are DML.",
                "difficulty": "EASY"
            },
            {
                "question": "What does SQL stand for?",
                "options": ["Structured Query Language", "Simple Query Language", "Standard Query Language", "Sequential Query Language"],
                "correct": 0,
                "explanation": "SQL stands for Structured Query Language.",
                "difficulty": "EASY"
            },
        ],
        ("CSE-301-LAB", "SQL Joins"): [
            {
                "question": "Which JOIN returns only matching rows from both tables?",
                "options": ["LEFT JOIN", "RIGHT JOIN", "INNER JOIN", "FULL JOIN"],
                "correct": 2,
                "explanation": "INNER JOIN returns only rows that have matching values in both tables.",
                "difficulty": "EASY"
            },
            {
                "question": "What does LEFT JOIN return?",
                "options": ["Only matching rows", "All rows from left table + matching from right", "All rows from right table", "All rows from both tables"],
                "correct": 1,
                "explanation": "LEFT JOIN returns all rows from left table and matching rows from right table.",
                "difficulty": "MEDIUM"
            },
        ],
        ("CSE-401-LAB", "Socket Programming - TCP"): [
            {
                "question": "What is a socket?",
                "options": ["A hardware device", "An endpoint for communication", "A network cable", "A protocol"],
                "correct": 1,
                "explanation": "A socket is an endpoint for sending/receiving data across a network.",
                "difficulty": "EASY"
            },
            {
                "question": "Which function is used to create a socket in Python?",
                "options": ["socket.create()", "socket.socket()", "socket.new()", "socket.open()"],
                "correct": 1,
                "explanation": "socket.socket() creates a new socket object in Python.",
                "difficulty": "EASY"
            },
            {
                "question": "What is the default port for HTTP?",
                "options": ["21", "22", "80", "443"],
                "correct": 2,
                "explanation": "HTTP uses port 80 by default; HTTPS uses 443.",
                "difficulty": "EASY"
            },
        ],
        ("CSE-501-LAB", "Linear Regression"): [
            {
                "question": "What type of problem does linear regression solve?",
                "options": ["Classification", "Regression", "Clustering", "Dimensionality reduction"],
                "correct": 1,
                "explanation": "Linear regression predicts continuous numerical values (regression).",
                "difficulty": "EASY"
            },
            {
                "question": "What is the loss function commonly used in linear regression?",
                "options": ["Cross-entropy", "Mean Squared Error", "Hinge loss", "Log loss"],
                "correct": 1,
                "explanation": "MSE (Mean Squared Error) is the standard loss function for linear regression.",
                "difficulty": "EASY"
            },
            {
                "question": "What does R² score measure?",
                "options": ["Error rate", "Proportion of variance explained", "Accuracy", "Precision"],
                "correct": 1,
                "explanation": "R² indicates how much variance in the target is explained by the model.",
                "difficulty": "MEDIUM"
            },
        ],
        ("IT-201-LAB", "OOP - Classes & Objects"): [
            {
                "question": "What is a class in Java?",
                "options": ["An object instance", "A blueprint for objects", "A method", "A variable"],
                "correct": 1,
                "explanation": "A class is a blueprint/template that defines the structure and behavior of objects.",
                "difficulty": "EASY"
            },
            {
                "question": "What keyword is used to create an object in Java?",
                "options": ["class", "new", "create", "object"],
                "correct": 1,
                "explanation": "The 'new' keyword allocates memory and creates a new object instance.",
                "difficulty": "EASY"
            },
            {
                "question": "What is encapsulation?",
                "options": ["Inheriting properties", "Hiding implementation details", "Method overloading", "Multiple inheritance"],
                "correct": 1,
                "explanation": "Encapsulation is bundling data and methods while hiding internal details.",
                "difficulty": "EASY"
            },
        ],
    }
    return mcqs_map.get((lab_code, topic_title), [
        {
            "question": f"Sample question for {topic_title}?",
            "options": ["Option A", "Option B", "Option C", "Option D"],
            "correct": 0,
            "explanation": "This is the correct answer.",
            "difficulty": "EASY"
        },
    ])

# ============================================================================
# CONCEPT CONTENT DATA
# ============================================================================

def get_concept_content(lab_code, topic_title):
    """Get comprehensive concept content for each topic"""
    content_map = {
        ("CSE-101-LAB", "Introduction to C Programming"): """# Introduction to C Programming

## What is C?

C is a general-purpose, procedural programming language developed by Dennis Ritchie at Bell Labs in 1972. It is one of the most widely used programming languages and forms the foundation for many modern languages like C++, Java, and Python.

## Why Learn C?

- **Foundation**: Understanding C helps you understand how computers work at a fundamental level
- **Performance**: C programs are fast and efficient
- **Portability**: C code can run on different platforms with minimal changes
- **Widespread Use**: Operating systems, embedded systems, and many applications are written in C

## Setting Up Your Environment

### Installing GCC (GNU Compiler Collection)

**On Ubuntu/Linux:**
```bash
sudo apt update
sudo apt install gcc
```

**On Windows:**
Install MinGW or use WSL (Windows Subsystem for Linux)

### Your First C Program

```c
#include <stdio.h>

int main() {
    printf("Hello, World!\\n");
    return 0;
}
```

### Understanding the Code

1. `#include <stdio.h>` - Includes the Standard Input/Output library
2. `int main()` - The main function where program execution begins
3. `printf()` - Function to print output to the console
4. `return 0` - Indicates successful program termination

## Compilation Process

The C compilation process involves four stages:

1. **Preprocessing**: Handles directives like `#include` and `#define`
2. **Compilation**: Converts C code to assembly language
3. **Assembly**: Converts assembly to machine code (object files)
4. **Linking**: Combines object files to create executable

### Compiling Your Program

```bash
gcc -o hello hello.c
./hello
```

## Key Takeaways

- C is a powerful, efficient programming language
- Every C program starts with the `main()` function
- Use `printf()` to display output
- Always compile your code before running it
""",
        ("CSE-101-LAB", "Data Types and Variables"): """# Data Types and Variables in C

## What are Data Types?

Data types specify the type of data that a variable can hold. C provides several built-in data types to work with different kinds of data.

## Primary Data Types

### Integer Types

| Type | Size (bytes) | Range |
|------|-------------|-------|
| char | 1 | -128 to 127 |
| short | 2 | -32,768 to 32,767 |
| int | 4 | -2,147,483,648 to 2,147,483,647 |
| long | 8 | Much larger range |

### Floating-Point Types

| Type | Size (bytes) | Precision |
|------|-------------|-----------|
| float | 4 | 6-7 decimal digits |
| double | 8 | 15-16 decimal digits |
| long double | 16 | 19-20 decimal digits |

## Declaring Variables

```c
// Syntax: data_type variable_name;
int age;
float salary;
char grade;

// Declaration with initialization
int count = 10;
float pi = 3.14159;
char letter = 'A';
```

## Constants

Constants are values that cannot be changed during program execution.

```c
// Using const keyword
const float PI = 3.14159;

// Using #define
#define MAX_SIZE 100
```

## Type Conversion

### Implicit Conversion (Automatic)
```c
int a = 10;
float b = a;  // int automatically converted to float
```

### Explicit Conversion (Type Casting)
```c
float x = 10.5;
int y = (int)x;  // Explicitly converts float to int (y = 10)
```

## Format Specifiers

| Specifier | Data Type |
|-----------|-----------|
| %d or %i | int |
| %f | float |
| %lf | double |
| %c | char |
| %s | string |
| %p | pointer |

## Example Program

```c
#include <stdio.h>

int main() {
    int age = 25;
    float height = 5.9;
    char grade = 'A';

    printf("Age: %d\\n", age);
    printf("Height: %.1f\\n", height);
    printf("Grade: %c\\n", grade);

    return 0;
}
```

## Key Takeaways

- Choose appropriate data types based on the data you need to store
- Use constants for values that shouldn't change
- Understand type conversion to avoid data loss
- Use correct format specifiers in printf/scanf
""",
        ("CSE-101-LAB", "Control Structures"): """# Control Structures in C

## Introduction

Control structures determine the flow of program execution. They allow you to make decisions, repeat actions, and control which statements execute.

## Decision Making Statements

### if Statement

```c
if (condition) {
    // code executes if condition is true
}
```

### if-else Statement

```c
if (condition) {
    // executes if condition is true
} else {
    // executes if condition is false
}
```

### if-else-if Ladder

```c
if (condition1) {
    // code block 1
} else if (condition2) {
    // code block 2
} else if (condition3) {
    // code block 3
} else {
    // default code block
}
```

### switch Statement

```c
switch (expression) {
    case value1:
        // code
        break;
    case value2:
        // code
        break;
    default:
        // default code
}
```

## Looping Statements

### for Loop

Best when you know how many times to iterate.

```c
for (initialization; condition; update) {
    // code to repeat
}

// Example: Print 1 to 5
for (int i = 1; i <= 5; i++) {
    printf("%d ", i);
}
```

### while Loop

Best when condition-based iteration is needed.

```c
while (condition) {
    // code to repeat
}

// Example
int i = 1;
while (i <= 5) {
    printf("%d ", i);
    i++;
}
```

### do-while Loop

Executes at least once, then checks condition.

```c
do {
    // code to repeat
} while (condition);

// Example
int i = 1;
do {
    printf("%d ", i);
    i++;
} while (i <= 5);
```

## Loop Control Statements

### break Statement
Exits the loop immediately.

```c
for (int i = 1; i <= 10; i++) {
    if (i == 5) break;
    printf("%d ", i);  // Prints: 1 2 3 4
}
```

### continue Statement
Skips current iteration and continues to next.

```c
for (int i = 1; i <= 5; i++) {
    if (i == 3) continue;
    printf("%d ", i);  // Prints: 1 2 4 5
}
```

## Nested Loops

```c
// Pattern printing
for (int i = 1; i <= 3; i++) {
    for (int j = 1; j <= i; j++) {
        printf("* ");
    }
    printf("\\n");
}
// Output:
// *
// * *
// * * *
```

## Key Takeaways

- Use if-else for simple decisions
- Use switch for multiple fixed choices
- Use for loop when count is known
- Use while when condition-based
- break exits loop, continue skips iteration
""",
        ("CSE-101-LAB", "Pointers"): """# Pointers in C

## What is a Pointer?

A pointer is a variable that stores the memory address of another variable. Pointers are one of the most powerful features of C.

## Why Use Pointers?

- **Dynamic Memory Allocation**: Allocate memory at runtime
- **Efficient Array/String Handling**: Access elements efficiently
- **Pass by Reference**: Modify variables in functions
- **Data Structures**: Implement linked lists, trees, etc.

## Declaring Pointers

```c
// Syntax: data_type *pointer_name;
int *p;      // Pointer to int
float *fp;   // Pointer to float
char *cp;    // Pointer to char
```

## Pointer Operators

### Address-of Operator (&)
Returns the memory address of a variable.

```c
int x = 10;
int *p = &x;  // p stores address of x
printf("Address of x: %p\\n", &x);
```

### Dereference Operator (*)
Accesses the value at the address stored in pointer.

```c
int x = 10;
int *p = &x;
printf("Value of x: %d\\n", *p);  // Prints 10
```

## Pointer Example

```c
#include <stdio.h>

int main() {
    int x = 10;
    int *p = &x;

    printf("Value of x: %d\\n", x);
    printf("Address of x: %p\\n", &x);
    printf("Value of p: %p\\n", p);
    printf("Value pointed by p: %d\\n", *p);

    // Modify x through pointer
    *p = 20;
    printf("New value of x: %d\\n", x);  // Prints 20

    return 0;
}
```

## Pointer Arithmetic

```c
int arr[] = {10, 20, 30, 40, 50};
int *p = arr;

printf("%d\\n", *p);       // 10
printf("%d\\n", *(p+1));   // 20
printf("%d\\n", *(p+2));   // 30
```

## NULL Pointer

A pointer that doesn't point to any valid memory location.

```c
int *p = NULL;

if (p == NULL) {
    printf("Pointer is NULL\\n");
}
```

## Pointers and Arrays

Arrays and pointers are closely related in C.

```c
int arr[] = {1, 2, 3, 4, 5};
int *p = arr;  // arr decays to pointer

// These are equivalent:
arr[i]  ==  *(arr + i)  ==  *(p + i)  ==  p[i]
```

## Pointers and Functions

### Pass by Reference

```c
void swap(int *a, int *b) {
    int temp = *a;
    *a = *b;
    *b = temp;
}

int main() {
    int x = 5, y = 10;
    swap(&x, &y);
    printf("x=%d, y=%d\\n", x, y);  // x=10, y=5
    return 0;
}
```

## Key Takeaways

- Pointers store memory addresses
- Use & to get address, * to dereference
- NULL pointer points to nothing
- Pointers enable pass-by-reference
- Be careful to avoid dangling pointers
""",
    }

    # Return specific content or generate default
    if (lab_code, topic_title) in content_map:
        return content_map[(lab_code, topic_title)]
    else:
        # Generate default content
        return f"""# {topic_title}

## Overview

This topic covers the fundamental concepts and practical applications.

## Learning Objectives

By the end of this topic, you will be able to:
- Understand the core concepts
- Apply the knowledge in practical scenarios
- Solve related problems

## Key Concepts

The main concepts covered in this topic include theoretical foundations and practical implementations.

## Practice

Practice the concepts through:
- MCQ questions to test understanding
- Coding problems to apply knowledge
- Hands-on exercises

## Summary

Review the key points and practice regularly to master this topic.
"""

# ============================================================================
# CODING PROBLEMS DATA
# ============================================================================

def get_coding_problems_for_topic(lab_code, topic_title):
    problems_map = {
        ("CSE-101-LAB", "Introduction to C Programming"): [
            {
                "title": "Hello World Program",
                "description": """Write a program that prints "Hello, World!" to the console.

**Input:** None

**Output:** Hello, World!

**Example:**
```
Output: Hello, World!
```""",
                "difficulty": "EASY",
                "languages": ["c"],
                "starter_code": {"c": '#include <stdio.h>\n\nint main() {\n    // Write your code here\n    return 0;\n}'},
                "test_cases": [{"input": "", "expected": "Hello, World!", "is_sample": True}],
                "hints": ["Use printf() function", "Don't forget the newline"]
            },
            {
                "title": "Sum of Two Numbers",
                "description": """Write a program that reads two integers and prints their sum.

**Input:** Two space-separated integers

**Output:** Sum of the two integers

**Example:**
```
Input: 5 3
Output: 8
```""",
                "difficulty": "EASY",
                "languages": ["c"],
                "starter_code": {"c": '#include <stdio.h>\n\nint main() {\n    int a, b;\n    // Read input and print sum\n    return 0;\n}'},
                "test_cases": [
                    {"input": "5 3", "expected": "8", "is_sample": True},
                    {"input": "10 20", "expected": "30", "is_sample": False},
                    {"input": "-5 5", "expected": "0", "is_sample": False}
                ],
                "hints": ["Use scanf() to read input", "Use printf() to print output"]
            },
        ],
        ("CSE-101-LAB", "Control Structures"): [
            {
                "title": "Even or Odd",
                "description": """Write a program that determines if a number is even or odd.

**Input:** A single integer N

**Output:** "Even" if N is even, "Odd" if N is odd

**Example:**
```
Input: 4
Output: Even
```""",
                "difficulty": "EASY",
                "languages": ["c", "python"],
                "starter_code": {
                    "c": '#include <stdio.h>\n\nint main() {\n    int n;\n    scanf("%d", &n);\n    // Check if even or odd\n    return 0;\n}',
                    "python": 'n = int(input())\n# Check if even or odd'
                },
                "test_cases": [
                    {"input": "4", "expected": "Even", "is_sample": True},
                    {"input": "7", "expected": "Odd", "is_sample": True},
                    {"input": "0", "expected": "Even", "is_sample": False}
                ],
                "hints": ["Use modulo operator %", "Even numbers have remainder 0 when divided by 2"]
            },
            {
                "title": "Factorial",
                "description": """Write a program to calculate the factorial of a number.

**Input:** A non-negative integer N (0 <= N <= 12)

**Output:** N!

**Example:**
```
Input: 5
Output: 120
```""",
                "difficulty": "EASY",
                "languages": ["c", "python"],
                "starter_code": {
                    "c": '#include <stdio.h>\n\nint main() {\n    int n;\n    scanf("%d", &n);\n    // Calculate factorial\n    return 0;\n}',
                    "python": 'n = int(input())\n# Calculate factorial'
                },
                "test_cases": [
                    {"input": "5", "expected": "120", "is_sample": True},
                    {"input": "0", "expected": "1", "is_sample": True},
                    {"input": "10", "expected": "3628800", "is_sample": False}
                ],
                "hints": ["Use a loop to multiply", "Remember: 0! = 1"]
            },
            {
                "title": "Prime Number Check",
                "description": """Write a program to check if a number is prime.

**Input:** A positive integer N (N >= 2)

**Output:** "Prime" if N is prime, "Not Prime" otherwise

**Example:**
```
Input: 7
Output: Prime
```""",
                "difficulty": "MEDIUM",
                "languages": ["c", "python"],
                "starter_code": {
                    "c": '#include <stdio.h>\n\nint main() {\n    int n;\n    scanf("%d", &n);\n    // Check if prime\n    return 0;\n}',
                    "python": 'n = int(input())\n# Check if prime'
                },
                "test_cases": [
                    {"input": "7", "expected": "Prime", "is_sample": True},
                    {"input": "4", "expected": "Not Prime", "is_sample": True},
                    {"input": "2", "expected": "Prime", "is_sample": False},
                    {"input": "97", "expected": "Prime", "is_sample": False}
                ],
                "hints": ["Check divisibility from 2 to sqrt(n)", "2 is the only even prime"]
            },
        ],
        ("CSE-201-LAB", "Linked Lists - Singly"): [
            {
                "title": "Reverse a Linked List",
                "description": """Given a singly linked list, reverse it and return the new head.

**Input:** Space-separated integers representing linked list nodes

**Output:** Reversed linked list

**Example:**
```
Input: 1 2 3 4 5
Output: 5 4 3 2 1
```""",
                "difficulty": "MEDIUM",
                "languages": ["c", "python", "java"],
                "starter_code": {
                    "python": '''class Node:
    def __init__(self, data):
        self.data = data
        self.next = None

def reverse_list(head):
    # Implement reversal
    pass

# Read input
data = list(map(int, input().split()))
# Create linked list and reverse
''',
                    "c": '''#include <stdio.h>
#include <stdlib.h>

struct Node {
    int data;
    struct Node* next;
};

struct Node* reverseList(struct Node* head) {
    // Implement reversal
    return head;
}

int main() {
    // Read input and call reverseList
    return 0;
}'''
                },
                "test_cases": [
                    {"input": "1 2 3 4 5", "expected": "5 4 3 2 1", "is_sample": True},
                    {"input": "1", "expected": "1", "is_sample": False},
                    {"input": "1 2", "expected": "2 1", "is_sample": False}
                ],
                "hints": ["Use three pointers: prev, current, next", "Iteratively change next pointers"]
            },
        ],
        ("CSE-201-LAB", "Stacks"): [
            {
                "title": "Valid Parentheses",
                "description": """Given a string containing just the characters '(', ')', '{', '}', '[' and ']', determine if the input string is valid.

A string is valid if:
1. Open brackets must be closed by the same type of brackets.
2. Open brackets must be closed in the correct order.

**Input:** A string of brackets

**Output:** "Valid" or "Invalid"

**Example:**
```
Input: ()[]{}
Output: Valid

Input: ([)]
Output: Invalid
```""",
                "difficulty": "MEDIUM",
                "languages": ["python", "java", "c"],
                "starter_code": {
                    "python": '''def is_valid(s):
    # Implement using stack
    pass

s = input()
print("Valid" if is_valid(s) else "Invalid")
''',
                },
                "test_cases": [
                    {"input": "()[]{}", "expected": "Valid", "is_sample": True},
                    {"input": "([)]", "expected": "Invalid", "is_sample": True},
                    {"input": "{[]}", "expected": "Valid", "is_sample": False},
                    {"input": "((()))", "expected": "Valid", "is_sample": False}
                ],
                "hints": ["Use a stack to track opening brackets", "Pop and match when closing bracket found"]
            },
        ],
        ("CSE-301-LAB", "SQL Basics"): [
            {
                "title": "Select All Employees",
                "description": """Write a SQL query to select all columns from the 'employees' table.

**Table: employees**
| id | name | department | salary |
|----|------|------------|--------|

**Output:** All rows and columns from employees table
""",
                "difficulty": "EASY",
                "languages": ["sql"],
                "starter_code": {"sql": "-- Write your SQL query here\n"},
                "test_cases": [{"input": "", "expected": "SELECT * FROM employees", "is_sample": True}],
                "hints": ["Use SELECT statement", "* selects all columns"]
            },
            {
                "title": "Filter by Salary",
                "description": """Write a SQL query to find all employees with salary greater than 50000.

**Table: employees**
| id | name | department | salary |

**Output:** All columns for employees with salary > 50000
""",
                "difficulty": "EASY",
                "languages": ["sql"],
                "starter_code": {"sql": "-- Write your SQL query here\n"},
                "test_cases": [{"input": "", "expected": "SELECT * FROM employees WHERE salary > 50000", "is_sample": True}],
                "hints": ["Use WHERE clause", "Use > for greater than comparison"]
            },
        ],
        ("CSE-501-LAB", "Linear Regression"): [
            {
                "title": "Simple Linear Regression",
                "description": """Implement simple linear regression from scratch.

Given training data (X, y), compute the slope (m) and intercept (b) for the line y = mx + b.

**Input:**
- First line: n (number of points)
- Next n lines: x y (space-separated)
- Last line: x_test (value to predict)

**Output:** Predicted y value (rounded to 2 decimal places)

**Example:**
```
Input:
3
1 2
2 4
3 6
4

Output: 8.00
```""",
                "difficulty": "MEDIUM",
                "languages": ["python"],
                "starter_code": {
                    "python": '''def linear_regression(X, y):
    # Calculate slope and intercept
    # Return m, b
    pass

n = int(input())
X, y = [], []
for _ in range(n):
    xi, yi = map(float, input().split())
    X.append(xi)
    y.append(yi)
x_test = float(input())

# Implement and predict
'''
                },
                "test_cases": [
                    {"input": "3\n1 2\n2 4\n3 6\n4", "expected": "8.00", "is_sample": True},
                    {"input": "4\n1 1\n2 2\n3 3\n4 4\n5", "expected": "5.00", "is_sample": False}
                ],
                "hints": ["Use the formula: m = Σ(xi-x̄)(yi-ȳ) / Σ(xi-x̄)²", "b = ȳ - m*x̄"]
            },
        ],
    }
    return problems_map.get((lab_code, topic_title), [])

# ============================================================================
# MAIN SEED FUNCTION
# ============================================================================

def seed_all_data():
    print("Starting seed process...")

    # Clear existing data
    print("Clearing existing lab data...")
    session.execute(text("DELETE FROM lab_coding_submissions"))
    session.execute(text("DELETE FROM lab_mcq_responses"))
    session.execute(text("DELETE FROM lab_quiz_sessions"))
    session.execute(text("DELETE FROM lab_topic_progress"))
    session.execute(text("DELETE FROM lab_enrollments"))
    session.execute(text("DELETE FROM lab_coding_problems"))
    session.execute(text("DELETE FROM lab_mcqs"))
    session.execute(text("DELETE FROM lab_topics"))
    session.execute(text("DELETE FROM labs"))
    session.commit()
    print("Cleared existing data.")

    labs_created = 0
    topics_created = 0
    mcqs_created = 0
    problems_created = 0

    for lab_data in labs_data:
        # Create lab
        lab_id = generate_uuid()
        lab_name = lab_data["name"].replace("'", "''")
        lab_desc = lab_data.get("description", "").replace("'", "''")
        tech_json = json.dumps(lab_data.get("technologies", []))
        session.execute(text(f"""
            INSERT INTO labs (id, name, code, description, branch, semester, technologies,
                            total_topics, total_mcqs, total_coding_problems, is_active, created_at, updated_at)
            VALUES ('{lab_id}', '{lab_name}', '{lab_data["code"]}',
                    '{lab_desc}', '{lab_data["branch"]}', '{lab_data["semester"]}',
                    '{tech_json}',
                    0, 0, 0, true, NOW(), NOW())
        """))
        labs_created += 1
        print(f"Created lab: {lab_data['name']}")

        # Get topics for this lab
        topics = get_topics_for_lab(lab_data["code"])
        lab_mcq_count = 0
        lab_problem_count = 0

        for i, topic_data in enumerate(topics):
            topic_id = generate_uuid()
            concept_content = get_concept_content(lab_data["code"], topic_data["title"]).replace("'", "''")

            # Video URL set to NULL - can be populated with institution's own content
            video_url_sql = "NULL"

            session.execute(text(f"""
                INSERT INTO lab_topics (id, lab_id, title, description, week_number, order_index,
                                       concept_content, video_url, mcq_count, coding_count, is_active, created_at, updated_at)
                VALUES ('{topic_id}', '{lab_id}', '{topic_data["title"]}', '{topic_data["description"]}',
                        {topic_data["week"]}, {i}, '{concept_content}', {video_url_sql}, 0, 0, true, NOW(), NOW())
            """))
            topics_created += 1

            # Add MCQs for this topic
            mcqs = get_mcqs_for_topic(lab_data["code"], topic_data["title"])
            topic_mcq_count = 0
            for mcq in mcqs:
                mcq_id = generate_uuid()
                options_json = json.dumps(mcq["options"]).replace("'", "''")
                question_text = mcq["question"].replace("'", "''")
                explanation = mcq.get("explanation", "").replace("'", "''")

                session.execute(text(f"""
                    INSERT INTO lab_mcqs (id, topic_id, question_text, options, correct_option,
                                         explanation, difficulty, marks, time_limit_seconds, is_active, created_at)
                    VALUES ('{mcq_id}', '{topic_id}', '{question_text}', '{options_json}',
                            {mcq["correct"]}, '{explanation}', '{mcq.get("difficulty", "MEDIUM")}',
                            1.0, 60, true, NOW())
                """))
                mcqs_created += 1
                topic_mcq_count += 1

            # Add coding problems for this topic
            problems = get_coding_problems_for_topic(lab_data["code"], topic_data["title"])
            topic_problem_count = 0
            for prob in problems:
                prob_id = generate_uuid()
                title = prob["title"].replace("'", "''")
                description = prob["description"].replace("'", "''")
                languages_json = json.dumps(prob["languages"]).replace("'", "''")
                starter_code_json = json.dumps(prob.get("starter_code", {})).replace("'", "''")
                test_cases_json = json.dumps(prob["test_cases"]).replace("'", "''")
                hints_json = json.dumps(prob.get("hints", [])).replace("'", "''")

                session.execute(text(f"""
                    INSERT INTO lab_coding_problems (id, topic_id, title, description, difficulty,
                                                    max_score, supported_languages, starter_code, test_cases,
                                                    hints, time_limit_ms, memory_limit_mb, is_active, created_at, updated_at)
                    VALUES ('{prob_id}', '{topic_id}', '{title}', '{description}', '{prob["difficulty"]}',
                            100, '{languages_json}', '{starter_code_json}', '{test_cases_json}',
                            '{hints_json}', 2000, 256, true, NOW(), NOW())
                """))
                problems_created += 1
                topic_problem_count += 1

            # Update topic counts
            session.execute(text(f"""
                UPDATE lab_topics SET mcq_count = {topic_mcq_count}, coding_count = {topic_problem_count}
                WHERE id = '{topic_id}'
            """))

            lab_mcq_count += topic_mcq_count
            lab_problem_count += topic_problem_count

        # Update lab counts
        session.execute(text(f"""
            UPDATE labs SET total_topics = {len(topics)}, total_mcqs = {lab_mcq_count},
                           total_coding_problems = {lab_problem_count}
            WHERE id = '{lab_id}'
        """))

    session.commit()

    print("\n" + "="*50)
    print("SEED COMPLETE!")
    print("="*50)
    print(f"Labs created: {labs_created}")
    print(f"Topics created: {topics_created}")
    print(f"MCQs created: {mcqs_created}")
    print(f"Coding Problems created: {problems_created}")
    print("="*50)

if __name__ == "__main__":
    seed_all_data()
    session.close()
