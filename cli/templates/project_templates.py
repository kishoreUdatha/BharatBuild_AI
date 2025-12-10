"""
Project Templates for Android, iOS, Blockchain, Go, Rust, Cybersecurity
"""

from typing import Dict, List, Any

PROJECT_TEMPLATES: Dict[str, Dict[str, Any]] = {

    # ==========================================
    # ANDROID - Kotlin + Jetpack Compose
    # ==========================================
    "android-compose": {
        "name": "Android Jetpack Compose",
        "description": "Modern Android app with Kotlin, Jetpack Compose, MVVM",
        "category": "Mobile",
        "files": {
            "app/build.gradle.kts": '''plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("kotlin-kapt")
    id("dagger.hilt.android.plugin")
}

android {
    namespace = "com.example.app"
    compileSdk = 34

    defaultConfig {
        applicationId = "com.example.app"
        minSdk = 24
        targetSdk = 34
        versionCode = 1
        versionName = "1.0"
    }

    buildFeatures {
        compose = true
    }

    composeOptions {
        kotlinCompilerExtensionVersion = "1.5.0"
    }
}

dependencies {
    // Compose
    implementation(platform("androidx.compose:compose-bom:2024.01.00"))
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.material3:material3")
    implementation("androidx.compose.ui:ui-tooling-preview")
    implementation("androidx.activity:activity-compose:1.8.2")
    implementation("androidx.navigation:navigation-compose:2.7.6")

    // ViewModel
    implementation("androidx.lifecycle:lifecycle-viewmodel-compose:2.7.0")
    implementation("androidx.lifecycle:lifecycle-runtime-compose:2.7.0")

    // Hilt
    implementation("com.google.dagger:hilt-android:2.48")
    kapt("com.google.dagger:hilt-compiler:2.48")
    implementation("androidx.hilt:hilt-navigation-compose:1.1.0")

    // Retrofit
    implementation("com.squareup.retrofit2:retrofit:2.9.0")
    implementation("com.squareup.retrofit2:converter-gson:2.9.0")

    // Room
    implementation("androidx.room:room-runtime:2.6.1")
    implementation("androidx.room:room-ktx:2.6.1")
    kapt("androidx.room:room-compiler:2.6.1")

    // Coroutines
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.7.3")
}
''',
            "app/src/main/kotlin/com/example/app/MainActivity.kt": '''package com.example.app

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.navigation.compose.rememberNavController
import dagger.hilt.android.AndroidEntryPoint

@AndroidEntryPoint
class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            MaterialTheme {
                Surface(modifier = Modifier.fillMaxSize()) {
                    AppNavigation()
                }
            }
        }
    }
}

@Composable
fun AppNavigation() {
    val navController = rememberNavController()
    // Add your navigation here
    HomeScreen()
}

@Composable
fun HomeScreen() {
    Column(
        modifier = Modifier.fillMaxSize().padding(16.dp),
        verticalArrangement = Arrangement.Center
    ) {
        Text("Welcome to Android App!", style = MaterialTheme.typography.headlineMedium)
        Spacer(modifier = Modifier.height(16.dp))
        Button(onClick = { }) {
            Text("Get Started")
        }
    }
}
''',
            "app/src/main/kotlin/com/example/app/data/repository/Repository.kt": '''package com.example.app.data.repository

import kotlinx.coroutines.flow.Flow
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class MainRepository @Inject constructor(
    private val api: ApiService,
    private val database: AppDatabase
) {
    // Add repository methods here
}
''',
            "app/src/main/kotlin/com/example/app/ui/viewmodel/MainViewModel.kt": '''package com.example.app.ui.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.*
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltViewModel
class MainViewModel @Inject constructor(
    private val repository: MainRepository
) : ViewModel() {

    private val _uiState = MutableStateFlow(UiState())
    val uiState: StateFlow<UiState> = _uiState.asStateFlow()

    data class UiState(
        val isLoading: Boolean = false,
        val error: String? = null,
        val data: List<String> = emptyList()
    )
}
''',
            "README.md": '''# Android Jetpack Compose App

## Tech Stack
- Kotlin
- Jetpack Compose
- MVVM Architecture
- Hilt (Dependency Injection)
- Room (Local Database)
- Retrofit (Networking)
- Coroutines + Flow

## Setup
1. Open in Android Studio
2. Sync Gradle
3. Run on emulator or device

## Structure
```
app/
├── data/
│   ├── local/      # Room database
│   ├── remote/     # Retrofit API
│   └── repository/ # Repository pattern
├── di/             # Hilt modules
├── ui/
│   ├── screens/    # Compose screens
│   └── viewmodel/  # ViewModels
└── utils/          # Utilities
```
'''
        }
    },

    # ==========================================
    # iOS - Swift + SwiftUI
    # ==========================================
    "ios-swiftui": {
        "name": "iOS SwiftUI App",
        "description": "Modern iOS app with SwiftUI, MVVM, Combine",
        "category": "Mobile",
        "files": {
            "App/MyApp.swift": '''import SwiftUI

@main
struct MyApp: App {
    @StateObject private var appState = AppState()

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(appState)
        }
    }
}

class AppState: ObservableObject {
    @Published var isLoggedIn = false
    @Published var user: User?
}

struct User: Codable, Identifiable {
    let id: String
    let name: String
    let email: String
}
''',
            "App/ContentView.swift": '''import SwiftUI

struct ContentView: View {
    @EnvironmentObject var appState: AppState

    var body: some View {
        NavigationStack {
            VStack(spacing: 20) {
                Text("Welcome to iOS App!")
                    .font(.largeTitle)
                    .fontWeight(.bold)

                Text("Built with SwiftUI")
                    .font(.subheadline)
                    .foregroundColor(.secondary)

                Button(action: {
                    // Action
                }) {
                    Text("Get Started")
                        .frame(maxWidth: .infinity)
                        .padding()
                        .background(Color.blue)
                        .foregroundColor(.white)
                        .cornerRadius(10)
                }
                .padding(.horizontal, 40)
            }
            .padding()
            .navigationTitle("Home")
        }
    }
}

#Preview {
    ContentView()
        .environmentObject(AppState())
}
''',
            "App/ViewModels/HomeViewModel.swift": '''import Foundation
import Combine

@MainActor
class HomeViewModel: ObservableObject {
    @Published var items: [Item] = []
    @Published var isLoading = false
    @Published var errorMessage: String?

    private let apiService: APIService
    private var cancellables = Set<AnyCancellable>()

    init(apiService: APIService = APIService()) {
        self.apiService = apiService
    }

    func fetchData() async {
        isLoading = true
        errorMessage = nil

        do {
            items = try await apiService.fetchItems()
        } catch {
            errorMessage = error.localizedDescription
        }

        isLoading = false
    }
}

struct Item: Codable, Identifiable {
    let id: String
    let title: String
    let description: String
}
''',
            "App/Services/APIService.swift": '''import Foundation

actor APIService {
    private let baseURL = "https://api.example.com"
    private let decoder = JSONDecoder()

    func fetchItems() async throws -> [Item] {
        guard let url = URL(string: "\\(baseURL)/items") else {
            throw APIError.invalidURL
        }

        let (data, response) = try await URLSession.shared.data(from: url)

        guard let httpResponse = response as? HTTPURLResponse,
              httpResponse.statusCode == 200 else {
            throw APIError.invalidResponse
        }

        return try decoder.decode([Item].self, from: data)
    }
}

enum APIError: Error {
    case invalidURL
    case invalidResponse
    case decodingError
}
''',
            "Package.swift": '''// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "MyApp",
    platforms: [.iOS(.v17), .macOS(.v14)],
    products: [
        .library(name: "MyApp", targets: ["MyApp"]),
    ],
    dependencies: [
        // Add dependencies here
    ],
    targets: [
        .target(name: "MyApp", dependencies: []),
        .testTarget(name: "MyAppTests", dependencies: ["MyApp"]),
    ]
)
''',
            "README.md": '''# iOS SwiftUI App

## Tech Stack
- Swift 5.9
- SwiftUI
- MVVM Architecture
- Combine
- async/await
- Swift Concurrency

## Requirements
- Xcode 15+
- iOS 17+

## Setup
1. Open .xcodeproj in Xcode
2. Select target device
3. Build and Run (Cmd+R)

## Structure
```
App/
├── Models/         # Data models
├── Views/          # SwiftUI views
├── ViewModels/     # MVVM ViewModels
├── Services/       # API & services
└── Utils/          # Utilities
```
'''
        }
    },

    # ==========================================
    # BLOCKCHAIN - Hardhat + Solidity
    # ==========================================
    "blockchain-hardhat": {
        "name": "Blockchain DApp (Hardhat + Solidity)",
        "description": "Ethereum smart contracts with Hardhat, Solidity, React frontend",
        "category": "Blockchain",
        "files": {
            "contracts/Token.sol": '''// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

contract MyToken is ERC20, Ownable {
    constructor(uint256 initialSupply) ERC20("MyToken", "MTK") Ownable(msg.sender) {
        _mint(msg.sender, initialSupply * 10 ** decimals());
    }

    function mint(address to, uint256 amount) public onlyOwner {
        _mint(to, amount);
    }
}
''',
            "contracts/NFT.sol": '''// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import "@openzeppelin/contracts/token/ERC721/extensions/ERC721URIStorage.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

contract MyNFT is ERC721, ERC721URIStorage, Ownable {
    uint256 private _nextTokenId;

    constructor() ERC721("MyNFT", "MNFT") Ownable(msg.sender) {}

    function safeMint(address to, string memory uri) public onlyOwner {
        uint256 tokenId = _nextTokenId++;
        _safeMint(to, tokenId);
        _setTokenURI(tokenId, uri);
    }

    function tokenURI(uint256 tokenId) public view override(ERC721, ERC721URIStorage) returns (string memory) {
        return super.tokenURI(tokenId);
    }

    function supportsInterface(bytes4 interfaceId) public view override(ERC721, ERC721URIStorage) returns (bool) {
        return super.supportsInterface(interfaceId);
    }
}
''',
            "hardhat.config.ts": '''import { HardhatUserConfig } from "hardhat/config";
import "@nomicfoundation/hardhat-toolbox";
import * as dotenv from "dotenv";

dotenv.config();

const config: HardhatUserConfig = {
  solidity: {
    version: "0.8.20",
    settings: {
      optimizer: { enabled: true, runs: 200 }
    }
  },
  networks: {
    hardhat: {},
    sepolia: {
      url: process.env.SEPOLIA_RPC_URL || "",
      accounts: process.env.PRIVATE_KEY ? [process.env.PRIVATE_KEY] : []
    },
    mainnet: {
      url: process.env.MAINNET_RPC_URL || "",
      accounts: process.env.PRIVATE_KEY ? [process.env.PRIVATE_KEY] : []
    }
  },
  etherscan: {
    apiKey: process.env.ETHERSCAN_API_KEY
  }
};

export default config;
''',
            "scripts/deploy.ts": '''import { ethers } from "hardhat";

async function main() {
  console.log("Deploying contracts...");

  // Deploy Token
  const Token = await ethers.getContractFactory("MyToken");
  const token = await Token.deploy(1000000); // 1M tokens
  await token.waitForDeployment();
  console.log("Token deployed to:", await token.getAddress());

  // Deploy NFT
  const NFT = await ethers.getContractFactory("MyNFT");
  const nft = await NFT.deploy();
  await nft.waitForDeployment();
  console.log("NFT deployed to:", await nft.getAddress());
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
''',
            "test/Token.test.ts": '''import { expect } from "chai";
import { ethers } from "hardhat";
import { MyToken } from "../typechain-types";

describe("MyToken", function () {
  let token: MyToken;
  let owner: any;
  let addr1: any;

  beforeEach(async function () {
    [owner, addr1] = await ethers.getSigners();
    const Token = await ethers.getContractFactory("MyToken");
    token = await Token.deploy(1000000);
  });

  it("Should have correct name and symbol", async function () {
    expect(await token.name()).to.equal("MyToken");
    expect(await token.symbol()).to.equal("MTK");
  });

  it("Should mint initial supply to owner", async function () {
    const balance = await token.balanceOf(owner.address);
    expect(balance).to.equal(ethers.parseEther("1000000"));
  });

  it("Should transfer tokens", async function () {
    await token.transfer(addr1.address, ethers.parseEther("100"));
    expect(await token.balanceOf(addr1.address)).to.equal(ethers.parseEther("100"));
  });
});
''',
            "package.json": '''{
  "name": "blockchain-dapp",
  "version": "1.0.0",
  "scripts": {
    "compile": "hardhat compile",
    "test": "hardhat test",
    "deploy:local": "hardhat run scripts/deploy.ts --network localhost",
    "deploy:sepolia": "hardhat run scripts/deploy.ts --network sepolia",
    "node": "hardhat node"
  },
  "devDependencies": {
    "@nomicfoundation/hardhat-toolbox": "^4.0.0",
    "@openzeppelin/contracts": "^5.0.0",
    "dotenv": "^16.3.1",
    "hardhat": "^2.19.0",
    "typescript": "^5.3.0"
  }
}
''',
            "README.md": '''# Blockchain DApp

## Tech Stack
- Solidity 0.8.20
- Hardhat
- OpenZeppelin Contracts
- TypeScript
- Ethers.js

## Setup
```bash
npm install
npx hardhat compile
npx hardhat test
```

## Deploy
```bash
# Local
npx hardhat node
npx hardhat run scripts/deploy.ts --network localhost

# Testnet
npx hardhat run scripts/deploy.ts --network sepolia
```

## Contracts
- `MyToken.sol` - ERC20 Token
- `MyNFT.sol` - ERC721 NFT
'''
        }
    },

    # ==========================================
    # SOLANA - Anchor + Rust
    # ==========================================
    "solana-anchor": {
        "name": "Solana Program (Anchor)",
        "description": "Solana smart contracts with Anchor framework",
        "category": "Blockchain",
        "files": {
            "programs/my_program/src/lib.rs": '''use anchor_lang::prelude::*;

declare_id!("Fg6PaFpoGXkYsidMpWTK6W2BeZ7FEfcYkg476zPFsLnS");

#[program]
pub mod my_program {
    use super::*;

    pub fn initialize(ctx: Context<Initialize>, data: u64) -> Result<()> {
        let my_account = &mut ctx.accounts.my_account;
        my_account.data = data;
        my_account.authority = ctx.accounts.authority.key();
        Ok(())
    }

    pub fn update(ctx: Context<Update>, new_data: u64) -> Result<()> {
        let my_account = &mut ctx.accounts.my_account;
        my_account.data = new_data;
        Ok(())
    }
}

#[derive(Accounts)]
pub struct Initialize<'info> {
    #[account(
        init,
        payer = authority,
        space = 8 + 8 + 32
    )]
    pub my_account: Account<'info, MyAccount>,
    #[account(mut)]
    pub authority: Signer<'info>,
    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
pub struct Update<'info> {
    #[account(mut, has_one = authority)]
    pub my_account: Account<'info, MyAccount>,
    pub authority: Signer<'info>,
}

#[account]
pub struct MyAccount {
    pub data: u64,
    pub authority: Pubkey,
}
''',
            "Anchor.toml": '''[features]
seeds = false
skip-lint = false

[programs.localnet]
my_program = "Fg6PaFpoGXkYsidMpWTK6W2BeZ7FEfcYkg476zPFsLnS"

[programs.devnet]
my_program = "Fg6PaFpoGXkYsidMpWTK6W2BeZ7FEfcYkg476zPFsLnS"

[registry]
url = "https://api.apr.dev"

[provider]
cluster = "Localnet"
wallet = "~/.config/solana/id.json"

[scripts]
test = "yarn run ts-mocha -p ./tsconfig.json -t 1000000 tests/**/*.ts"
''',
            "Cargo.toml": '''[workspace]
members = ["programs/*"]
resolver = "2"

[profile.release]
overflow-checks = true
lto = "fat"
codegen-units = 1

[profile.release.build-override]
opt-level = 3
incremental = false
codegen-units = 1
''',
            "tests/my_program.ts": '''import * as anchor from "@coral-xyz/anchor";
import { Program } from "@coral-xyz/anchor";
import { MyProgram } from "../target/types/my_program";
import { expect } from "chai";

describe("my_program", () => {
  const provider = anchor.AnchorProvider.env();
  anchor.setProvider(provider);

  const program = anchor.workspace.MyProgram as Program<MyProgram>;
  const myAccount = anchor.web3.Keypair.generate();

  it("Initializes account", async () => {
    await program.methods
      .initialize(new anchor.BN(42))
      .accounts({
        myAccount: myAccount.publicKey,
        authority: provider.wallet.publicKey,
        systemProgram: anchor.web3.SystemProgram.programId,
      })
      .signers([myAccount])
      .rpc();

    const account = await program.account.myAccount.fetch(myAccount.publicKey);
    expect(account.data.toNumber()).to.equal(42);
  });

  it("Updates account", async () => {
    await program.methods
      .update(new anchor.BN(100))
      .accounts({
        myAccount: myAccount.publicKey,
        authority: provider.wallet.publicKey,
      })
      .rpc();

    const account = await program.account.myAccount.fetch(myAccount.publicKey);
    expect(account.data.toNumber()).to.equal(100);
  });
});
''',
            "package.json": '''{
  "name": "solana-anchor-project",
  "version": "1.0.0",
  "scripts": {
    "build": "anchor build",
    "test": "anchor test",
    "deploy": "anchor deploy"
  },
  "dependencies": {
    "@coral-xyz/anchor": "^0.29.0",
    "@solana/web3.js": "^1.87.0"
  },
  "devDependencies": {
    "@types/chai": "^4.3.0",
    "@types/mocha": "^10.0.0",
    "chai": "^4.3.0",
    "mocha": "^10.2.0",
    "ts-mocha": "^10.0.0",
    "typescript": "^5.3.0"
  }
}
''',
            "README.md": '''# Solana Anchor Project

## Tech Stack
- Rust
- Anchor Framework
- Solana Web3.js
- TypeScript

## Setup
```bash
# Install Solana CLI
sh -c "$(curl -sSfL https://release.solana.com/stable/install)"

# Install Anchor
cargo install --git https://github.com/coral-xyz/anchor anchor-cli

# Build
anchor build

# Test
anchor test
```

## Deploy
```bash
# Devnet
solana config set --url devnet
anchor deploy

# Mainnet
solana config set --url mainnet-beta
anchor deploy
```
'''
        }
    },

    # ==========================================
    # GO - Gin + Clean Architecture
    # ==========================================
    "go-gin": {
        "name": "Go REST API (Gin)",
        "description": "Go backend with Gin, Clean Architecture, PostgreSQL",
        "category": "Backend",
        "files": {
            "main.go": '''package main

import (
	"log"
	"os"

	"github.com/gin-gonic/gin"
	"github.com/joho/godotenv"
)

func main() {
	// Load .env
	godotenv.Load()

	// Setup router
	r := gin.Default()

	// Health check
	r.GET("/health", func(c *gin.Context) {
		c.JSON(200, gin.H{"status": "ok"})
	})

	// API routes
	api := r.Group("/api/v1")
	{
		api.GET("/users", GetUsers)
		api.GET("/users/:id", GetUser)
		api.POST("/users", CreateUser)
		api.PUT("/users/:id", UpdateUser)
		api.DELETE("/users/:id", DeleteUser)
	}

	// Start server
	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}
	log.Printf("Server starting on port %s", port)
	r.Run(":" + port)
}
''',
            "handlers.go": '''package main

import (
	"net/http"

	"github.com/gin-gonic/gin"
)

type User struct {
	ID    string `json:"id"`
	Name  string `json:"name" binding:"required"`
	Email string `json:"email" binding:"required,email"`
}

var users = []User{}

func GetUsers(c *gin.Context) {
	c.JSON(http.StatusOK, users)
}

func GetUser(c *gin.Context) {
	id := c.Param("id")
	for _, user := range users {
		if user.ID == id {
			c.JSON(http.StatusOK, user)
			return
		}
	}
	c.JSON(http.StatusNotFound, gin.H{"error": "User not found"})
}

func CreateUser(c *gin.Context) {
	var user User
	if err := c.ShouldBindJSON(&user); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	user.ID = generateID()
	users = append(users, user)
	c.JSON(http.StatusCreated, user)
}

func UpdateUser(c *gin.Context) {
	id := c.Param("id")
	var input User
	if err := c.ShouldBindJSON(&input); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}
	for i, user := range users {
		if user.ID == id {
			users[i].Name = input.Name
			users[i].Email = input.Email
			c.JSON(http.StatusOK, users[i])
			return
		}
	}
	c.JSON(http.StatusNotFound, gin.H{"error": "User not found"})
}

func DeleteUser(c *gin.Context) {
	id := c.Param("id")
	for i, user := range users {
		if user.ID == id {
			users = append(users[:i], users[i+1:]...)
			c.JSON(http.StatusOK, gin.H{"message": "User deleted"})
			return
		}
	}
	c.JSON(http.StatusNotFound, gin.H{"error": "User not found"})
}

func generateID() string {
	return fmt.Sprintf("%d", time.Now().UnixNano())
}
''',
            "go.mod": '''module myapp

go 1.21

require (
	github.com/gin-gonic/gin v1.9.1
	github.com/joho/godotenv v1.5.1
	gorm.io/driver/postgres v1.5.4
	gorm.io/gorm v1.25.5
)
''',
            "Dockerfile": '''FROM golang:1.21-alpine AS builder
WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -o main .

FROM alpine:latest
RUN apk --no-cache add ca-certificates
WORKDIR /root/
COPY --from=builder /app/main .
EXPOSE 8080
CMD ["./main"]
''',
            "README.md": '''# Go REST API

## Tech Stack
- Go 1.21
- Gin Framework
- GORM (PostgreSQL)
- Clean Architecture

## Setup
```bash
go mod download
go run .
```

## API Endpoints
- GET /api/v1/users
- GET /api/v1/users/:id
- POST /api/v1/users
- PUT /api/v1/users/:id
- DELETE /api/v1/users/:id

## Docker
```bash
docker build -t myapp .
docker run -p 8080:8080 myapp
```
'''
        }
    },

    # ==========================================
    # RUST - Actix-web
    # ==========================================
    "rust-actix": {
        "name": "Rust REST API (Actix-web)",
        "description": "Rust backend with Actix-web, SQLx, PostgreSQL",
        "category": "Backend",
        "files": {
            "src/main.rs": '''use actix_web::{web, App, HttpServer, HttpResponse, middleware};
use serde::{Deserialize, Serialize};
use std::sync::Mutex;

mod handlers;
mod models;

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct User {
    pub id: String,
    pub name: String,
    pub email: String,
}

pub struct AppState {
    pub users: Mutex<Vec<User>>,
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    env_logger::init();

    let app_state = web::Data::new(AppState {
        users: Mutex::new(Vec::new()),
    });

    println!("Server running at http://localhost:8080");

    HttpServer::new(move || {
        App::new()
            .app_data(app_state.clone())
            .wrap(middleware::Logger::default())
            .route("/health", web::get().to(health_check))
            .service(
                web::scope("/api/v1")
                    .route("/users", web::get().to(handlers::get_users))
                    .route("/users", web::post().to(handlers::create_user))
                    .route("/users/{id}", web::get().to(handlers::get_user))
                    .route("/users/{id}", web::put().to(handlers::update_user))
                    .route("/users/{id}", web::delete().to(handlers::delete_user))
            )
    })
    .bind("0.0.0.0:8080")?
    .run()
    .await
}

async fn health_check() -> HttpResponse {
    HttpResponse::Ok().json(serde_json::json!({"status": "ok"}))
}
''',
            "src/handlers.rs": '''use actix_web::{web, HttpResponse};
use uuid::Uuid;
use crate::{AppState, User};

pub async fn get_users(data: web::Data<AppState>) -> HttpResponse {
    let users = data.users.lock().unwrap();
    HttpResponse::Ok().json(&*users)
}

pub async fn get_user(
    path: web::Path<String>,
    data: web::Data<AppState>
) -> HttpResponse {
    let id = path.into_inner();
    let users = data.users.lock().unwrap();

    match users.iter().find(|u| u.id == id) {
        Some(user) => HttpResponse::Ok().json(user),
        None => HttpResponse::NotFound().json(serde_json::json!({"error": "User not found"}))
    }
}

pub async fn create_user(
    body: web::Json<CreateUserRequest>,
    data: web::Data<AppState>
) -> HttpResponse {
    let mut users = data.users.lock().unwrap();

    let user = User {
        id: Uuid::new_v4().to_string(),
        name: body.name.clone(),
        email: body.email.clone(),
    };

    users.push(user.clone());
    HttpResponse::Created().json(user)
}

#[derive(serde::Deserialize)]
pub struct CreateUserRequest {
    pub name: String,
    pub email: String,
}
''',
            "Cargo.toml": '''[package]
name = "rust-api"
version = "0.1.0"
edition = "2021"

[dependencies]
actix-web = "4"
actix-rt = "2"
serde = { version = "1", features = ["derive"] }
serde_json = "1"
tokio = { version = "1", features = ["full"] }
uuid = { version = "1", features = ["v4"] }
env_logger = "0.10"
log = "0.4"
sqlx = { version = "0.7", features = ["runtime-tokio", "postgres"] }
dotenv = "0.15"
''',
            "Dockerfile": '''FROM rust:1.74 AS builder
WORKDIR /app
COPY . .
RUN cargo build --release

FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y libssl3 ca-certificates && rm -rf /var/lib/apt/lists/*
COPY --from=builder /app/target/release/rust-api /usr/local/bin/
EXPOSE 8080
CMD ["rust-api"]
''',
            "README.md": '''# Rust REST API

## Tech Stack
- Rust 1.74
- Actix-web
- SQLx (PostgreSQL)
- Serde

## Setup
```bash
cargo build
cargo run
```

## API Endpoints
- GET /api/v1/users
- POST /api/v1/users
- GET /api/v1/users/{id}
- PUT /api/v1/users/{id}
- DELETE /api/v1/users/{id}
'''
        }
    },

    # ==========================================
    # CYBERSECURITY - Python Tools
    # ==========================================
    "cybersecurity-toolkit": {
        "name": "Cybersecurity Toolkit",
        "description": "Python security tools: scanner, analyzer, pentesting utilities",
        "category": "Security",
        "files": {
            "scanner.py": '''"""
Network & Vulnerability Scanner
"""
import socket
import threading
from concurrent.futures import ThreadPoolExecutor
import ssl
import requests
from typing import List, Dict

class PortScanner:
    def __init__(self, target: str):
        self.target = target
        self.open_ports: List[int] = []

    def scan_port(self, port: int) -> bool:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex((self.target, port))
            sock.close()
            return result == 0
        except:
            return False

    def scan_range(self, start: int = 1, end: int = 1024, threads: int = 100) -> List[int]:
        """Scan port range with threading"""
        print(f"Scanning {self.target} ports {start}-{end}...")

        with ThreadPoolExecutor(max_workers=threads) as executor:
            futures = {executor.submit(self.scan_port, port): port for port in range(start, end + 1)}
            for future in futures:
                port = futures[future]
                if future.result():
                    self.open_ports.append(port)
                    print(f"[+] Port {port} is OPEN")

        return sorted(self.open_ports)

    def get_service(self, port: int) -> str:
        """Get service name for port"""
        common_ports = {
            21: "FTP", 22: "SSH", 23: "Telnet", 25: "SMTP",
            53: "DNS", 80: "HTTP", 110: "POP3", 143: "IMAP",
            443: "HTTPS", 445: "SMB", 3306: "MySQL", 5432: "PostgreSQL",
            6379: "Redis", 27017: "MongoDB", 8080: "HTTP-Proxy"
        }
        return common_ports.get(port, "Unknown")


class SSLAnalyzer:
    def __init__(self, host: str, port: int = 443):
        self.host = host
        self.port = port

    def analyze(self) -> Dict:
        """Analyze SSL/TLS configuration"""
        context = ssl.create_default_context()

        try:
            with socket.create_connection((self.host, self.port)) as sock:
                with context.wrap_socket(sock, server_hostname=self.host) as ssock:
                    cert = ssock.getpeercert()
                    cipher = ssock.cipher()
                    version = ssock.version()

                    return {
                        "host": self.host,
                        "version": version,
                        "cipher": cipher[0] if cipher else None,
                        "issuer": dict(x[0] for x in cert.get("issuer", [])),
                        "subject": dict(x[0] for x in cert.get("subject", [])),
                        "expires": cert.get("notAfter"),
                        "serial": cert.get("serialNumber")
                    }
        except Exception as e:
            return {"error": str(e)}


class VulnerabilityChecker:
    def __init__(self, target: str):
        self.target = target
        self.vulnerabilities: List[Dict] = []

    def check_headers(self) -> List[Dict]:
        """Check security headers"""
        security_headers = [
            "Strict-Transport-Security",
            "X-Content-Type-Options",
            "X-Frame-Options",
            "X-XSS-Protection",
            "Content-Security-Policy",
            "Referrer-Policy"
        ]

        try:
            resp = requests.get(self.target, timeout=10)
            missing = []

            for header in security_headers:
                if header not in resp.headers:
                    missing.append({
                        "type": "Missing Security Header",
                        "header": header,
                        "severity": "Medium"
                    })

            self.vulnerabilities.extend(missing)
            return missing
        except Exception as e:
            return [{"error": str(e)}]


if __name__ == "__main__":
    # Example usage
    target = "scanme.nmap.org"

    # Port scan
    scanner = PortScanner(target)
    open_ports = scanner.scan_range(1, 100)
    print(f"\\nOpen ports: {open_ports}")

    # SSL analysis
    ssl_analyzer = SSLAnalyzer(target, 443)
    ssl_info = ssl_analyzer.analyze()
    print(f"\\nSSL Info: {ssl_info}")
''',
            "password_tools.py": '''"""
Password Security Tools
"""
import hashlib
import secrets
import string
from typing import List, Tuple

def generate_password(length: int = 16,
                     use_upper: bool = True,
                     use_lower: bool = True,
                     use_digits: bool = True,
                     use_special: bool = True) -> str:
    """Generate secure random password"""
    chars = ""
    if use_upper:
        chars += string.ascii_uppercase
    if use_lower:
        chars += string.ascii_lowercase
    if use_digits:
        chars += string.digits
    if use_special:
        chars += "!@#$%^&*()_+-=[]{}|;:,.<>?"

    return ''.join(secrets.choice(chars) for _ in range(length))


def check_password_strength(password: str) -> Tuple[int, List[str]]:
    """Check password strength (0-100 score)"""
    score = 0
    feedback = []

    # Length
    if len(password) >= 8:
        score += 20
    if len(password) >= 12:
        score += 10
    if len(password) >= 16:
        score += 10
    else:
        feedback.append("Use at least 16 characters")

    # Complexity
    if any(c.isupper() for c in password):
        score += 15
    else:
        feedback.append("Add uppercase letters")

    if any(c.islower() for c in password):
        score += 15
    else:
        feedback.append("Add lowercase letters")

    if any(c.isdigit() for c in password):
        score += 15
    else:
        feedback.append("Add numbers")

    if any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
        score += 15
    else:
        feedback.append("Add special characters")

    return min(score, 100), feedback


def hash_password(password: str, algorithm: str = "sha256") -> str:
    """Hash password with specified algorithm"""
    algorithms = {
        "md5": hashlib.md5,
        "sha1": hashlib.sha1,
        "sha256": hashlib.sha256,
        "sha512": hashlib.sha512
    }
    hasher = algorithms.get(algorithm, hashlib.sha256)
    return hasher(password.encode()).hexdigest()


if __name__ == "__main__":
    # Generate password
    pwd = generate_password(20)
    print(f"Generated password: {pwd}")

    # Check strength
    score, feedback = check_password_strength(pwd)
    print(f"Strength: {score}/100")
    print(f"Feedback: {feedback}")
''',
            "requirements.txt": '''requests>=2.31.0
python-nmap>=0.7.1
cryptography>=41.0.0
scapy>=2.5.0
paramiko>=3.3.0
beautifulsoup4>=4.12.0
''',
            "README.md": '''# Cybersecurity Toolkit

## Tools Included
- **Port Scanner** - TCP port scanning with threading
- **SSL Analyzer** - SSL/TLS configuration analysis
- **Vulnerability Checker** - Security header checking
- **Password Tools** - Generation and strength checking

## Setup
```bash
pip install -r requirements.txt
```

## Usage
```python
from scanner import PortScanner, SSLAnalyzer

# Scan ports
scanner = PortScanner("target.com")
open_ports = scanner.scan_range(1, 1000)

# Analyze SSL
ssl = SSLAnalyzer("target.com")
info = ssl.analyze()
```

## Legal Notice
Only use on systems you have permission to test!
'''
        }
    }
}


def get_template(template_id: str) -> Dict[str, Any]:
    """Get a specific template by ID"""
    return PROJECT_TEMPLATES.get(template_id)


def list_templates(category: str = None) -> List[Dict[str, str]]:
    """List all templates, optionally filtered by category"""
    templates = []
    for tid, template in PROJECT_TEMPLATES.items():
        if category is None or template.get("category") == category:
            templates.append({
                "id": tid,
                "name": template["name"],
                "description": template["description"],
                "category": template["category"]
            })
    return templates


def get_categories() -> List[str]:
    """Get all template categories"""
    categories = set()
    for template in PROJECT_TEMPLATES.values():
        categories.add(template["category"])
    return sorted(list(categories))
