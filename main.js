import fs from "fs/promises";
import axios from "axios";
import readline from "readline";
import { getBanner } from "./config/banner.js";
import { colors } from "./config/colors.js";
import { Wallet } from "ethers";
import { HttpsProxyAgent } from "https-proxy-agent";
 
const CONFIG = {
  PING_INTERVAL: 720, // 12 hours in minutes
  get PING_INTERVAL_MS() {
    return this.PING_INTERVAL * 60 * 1000;
  },
};
 
readline.emitKeypressEvents(process.stdin);
process.stdin.setRawMode(true);
 
class ProxyManager {
  constructor() {
    this.proxies = [];
  }
 
  async initialize() {
    try {
      const data = await fs.readFile("proxy.txt", "utf8");
      this.proxies = data
        .split("\n")
        .filter((line) => line.trim() !== "")
        .map((line) => line.trim());
      return this.proxies;
    } catch (error) {
      console.error(
        `${colors.error}Error reading proxy.txt: ${error}${colors.reset}`
      );
      return [];
    }
  }
 
  getRandomProxy() {
    if (this.proxies.length === 0) return null;
    const randomIndex = Math.floor(Math.random() * this.proxies.length);
    return this.proxies[randomIndex];
  }
}
 
const countdown = async (seconds) => {
  return new Promise((resolve) => {
    let remaining = seconds;
    const interval = setInterval(() => {
      const hours = Math.floor(remaining / 3600);
      const mins = Math.floor((remaining % 3600) / 60);
      const secs = remaining % 60;
 
      process.stdout.write(
        `\r⏳ Next cycle in: ${hours.toString().padStart(2, "0")}:${mins
          .toString()
          .padStart(2, "0")}:${secs.toString().padStart(2, "0")}`
      );
 
      remaining--;
 
      if (remaining < 0) {
        clearInterval(interval);
        process.stdout.write("\r✅ Starting new cycle...                \n");
        resolve();
      }
    }, 1000);
  });
};
 
class WalletDashboard {
  constructor() {
    this.BATCH_SIZE = 50;
    this.wallets = [];
    this.selectedIndex = 0;
    this.isRunning = true;
    this.walletStats = new Map();
    this.privateKeys = new Map();
    this.renderTimeout = null;
    this.lastRender = 0;
    this.minRenderInterval = 100;
    this.proxyManager = new ProxyManager();
  }
 
  async initialize() {
    try {
      const [data] = await Promise.all([
        fs.readFile("data.txt", "utf8"),
        this.proxyManager.initialize(),
      ]);
 
      const privateKeys = data
        .split("\n")
        .map((line) => line.trim())
        .filter((line) => line.length > 30);
 
      this.wallets = [];
      this.privateKeys = new Map();
 
      for (const privateKey of privateKeys) {
        try {
          const wallet = new Wallet(privateKey);
          const address = wallet.address;
          const proxy = this.proxyManager.getRandomProxy();
 
          this.wallets.push(address);
          this.privateKeys.set(address, privateKey);
 
          this.walletStats.set(address, {
            status: "Starting",
            points: 0,
            error: null,
            proxy: proxy,
          });
        } catch (error) {
          console.error(
            `${colors.error}Error with key ${privateKey}: ${error.message}${colors.reset}`
          );
        }
      }
 
      if (this.wallets.length === 0) {
        throw new Error("No valid private keys found in data.txt");
      }
    } catch (error) {
      console.error(
        `${colors.error}Error initializing: ${error}${colors.reset}`
      );
      process.exit(1);
    }
  }
 
  getDashboardApi() {
    const proxy = this.proxyManager.getRandomProxy();
    const config = {
      baseURL: "https://dashboard.layeredge.io/api",
      headers: {
        accept: "*/*",
        "accept-language": "en-GB,en;q=0.9,en-US;q=0.8",
        "content-type": "application/json",
        origin: "https://dashboard.layeredge.io",
        referer: "https://dashboard.layeredge.io/",
        "user-agent":
          "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36",
      },
      timeout: 30000,
    };
 
    if (proxy) {
      config.httpsAgent = new HttpsProxyAgent(proxy);
      config.proxy = false;
    }
 
    return axios.create(config);
  }
 
  getApi() {
    const proxy = this.proxyManager.getRandomProxy();
    const config = {
      baseURL: "https://referralapi.layeredge.io/api",
      headers: {
        Accept: "*/*",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "en-US,en;q=0.9",
        "Content-Type": "application/json",
        Origin: "https://dashboard.layeredge.io",
        Referer: "https://dashboard.layeredge.io",
        "User-Agent":
          "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
      },
      timeout: 30000,
      maxRetries: 20,
      retryDelay: 2000,
      retryCondition: (error) => {
        return axios.isNetworkError(error) || error.code === "ETIMEDOUT";
      },
    };
 
    if (proxy) {
      config.httpsAgent = new HttpsProxyAgent(proxy);
      config.proxy = false;
    }
 
    return axios.create(config);
  }
 
  async signAndStop(wallet, privateKey) {
    try {
      const walletInstance = new Wallet(privateKey);
      const timestamp = Date.now();
      const message = `Node deactivation request for ${wallet} at ${timestamp}`;
      const sign = await walletInstance.signMessage(message);
 
      const response = await this.getApi().post(
        `/light-node/node-action/${wallet}/stop`,
        {
          sign: sign,
          timestamp: timestamp,
        }
      );
 
      return response.data?.message === "node action executed successfully";
    } catch (error) {
      // If 404 error, consider it as normal and return true
      if (error.response?.status === 404) {
        return true;
      }
 
      console.log(
        `Node deactivation attempted for ${wallet}: ${error.message}`
      );
      return false;
    }
  }
 
  async signAndStart(wallet, privateKey) {
    try {
      const walletInstance = new Wallet(privateKey);
      const timestamp = Date.now();
      const message = `Node activation request for ${wallet} at ${timestamp}`;
      const sign = await walletInstance.signMessage(message);
 
      const response = await this.getApi().post(
        `/light-node/node-action/${wallet}/start`,
        {
          sign: sign,
          timestamp: timestamp,
        }
      );
 
      return response.data?.message === "node action executed successfully";
    } catch (error) {
      throw new Error(`Node activation failed: ${error.message}`);
    }
  }
 
  async checkNodeStatus(wallet, retries = 20) {
    for (let i = 0; i < retries; i++) {
      try {
        const response = await this.getApi().get(
          `/light-node/node-status/${wallet}`
        );
        return response.data?.data?.startTimestamp !== null;
      } catch (error) {
        if (i === retries - 1) {
          if (error.code === "ETIMEDOUT" || error.code === "ECONNABORTED") {
            throw new Error("Connection timeout");
          }
          if (error.response?.status === 404) {
            throw new Error("Node not found");
          }
          throw new Error(`Check status failed: ${error.message}`);
        }
        await new Promise((resolve) => setTimeout(resolve, 2000));
        continue;
      }
    }
  }
 
  async checkPoints(wallet) {
    try {
      const response = await this.getApi().get(
        `/referral/wallet-details/${wallet}`
      );
      return response.data?.data?.nodePoints || 0;
    } catch (error) {
      throw new Error(`Check points failed: ${error.message}`);
    }
  }
 
  async updatePoints(wallet) {
    try {
      const isRunning = await this.checkNodeStatus(wallet);
      if (!isRunning) {
        throw new Error("Node not running");
      }
 
      const points = await this.checkPoints(wallet);
      return { nodePoints: points };
    } catch (error) {
      if (error.response) {
        switch (error.response.status) {
          case 500:
            throw new Error("Internal Server Error");
          case 504:
            throw new Error("Gateway Timeout");
          case 403:
            throw new Error("Node not activated");
          default:
            throw new Error(`Update points failed: ${error.message}`);
        }
      }
      throw error;
    }
  }
 
  updateWalletStatus(wallet, status, error = null) {
    const stats = this.walletStats.get(wallet);
    stats.status = status;
    stats.error = error;
 
    // Format the status line
    const statusColor = this.getStatusColor(status);
    const timestamp = new Date().toLocaleTimeString();
    const shortWallet = `${wallet.slice(0, 6)}...${wallet.slice(-4)}`;
    const statusLine = `[${timestamp}] Wallet ${shortWallet}: ${statusColor}${status}${colors.reset}`;
 
    if (error) {
      console.log(`${statusLine} - ${colors.error}${error}${colors.reset}`);
    } else {
      console.log(statusLine);
    }
  }
 
  async processWallet(wallet) {
    const stats = this.walletStats.get(wallet);
    let retryCount = 0;
    const maxRetries = 5;
 
    while (retryCount < maxRetries) {
      try {
        const privateKey = this.privateKeys.get(wallet);
        if (!privateKey) {
          throw new Error("Private key not found");
        }
 
        this.updateWalletStatus(wallet, "Stopping Node");
        await this.signAndStop(wallet, privateKey);
        await new Promise((resolve) => setTimeout(resolve, 5000));
 
        this.updateWalletStatus(wallet, "Checking Status");
        const isRunning = await this.checkNodeStatus(wallet);
 
        if (!isRunning) {
          this.updateWalletStatus(wallet, "Starting Node");
          await this.signAndStart(wallet, privateKey);
          await new Promise((resolve) => setTimeout(resolve, 5000));
        }
 
        this.updateWalletStatus(wallet, "Updating Points");
        const result = await this.updatePoints(wallet);
        stats.points = result.nodePoints || stats.points;
 
        const newProxy = this.proxyManager.getRandomProxy();
        stats.proxy = newProxy;
 
        this.updateWalletStatus(
          wallet,
          "Active",
          `Points: ${stats.points} | Proxy: ${newProxy}`
        );
        return true; // Success
      } catch (error) {
        retryCount++;
        this.updateWalletStatus(
          wallet,
          "Error",
          `Retry ${retryCount}/${maxRetries}: ${error.message}`
        );
 
        if (retryCount >= maxRetries) {
          console.error(`Max retries reached for wallet ${wallet}`);
          return false;
        }
 
        this.updateWalletStatus(wallet, "Waiting", `Retrying in 10s...`);
        await new Promise((resolve) => setTimeout(resolve, 10000));
      }
    }
  }
 
  async processBatch(batch) {
    const batchPromises = batch.map((wallet) => this.processWallet(wallet));
    await Promise.all(batchPromises);
  }
 
  getStatusColor(status) {
    switch (status) {
      case "Active":
        return colors.success;
      case "Error":
        return colors.error;
      case "Starting Node":
      case "Stopping Node":
      case "Checking Status":
      case "Updating Points":
        return colors.taskInProgress;
      case "Waiting":
        return colors.yellow;
      default:
        return colors.reset;
    }
  }
 
  async start() {
    process.on("SIGINT", () => {
      console.log(`\n${colors.info}Shutting down...${colors.reset}`);
      process.exit();
    });
 
    process.stdin.on("keypress", (str, key) => {
      if (key.ctrl && key.name === "c") {
        process.emit("SIGINT");
      }
    });
 
    await this.initialize();
    console.log(getBanner());
 
    while (this.isRunning) {
      // Process wallets in batches
      for (let i = 0; i < this.wallets.length; i += this.BATCH_SIZE) {
        const batch = this.wallets.slice(i, i + this.BATCH_SIZE);
        console.log(
          `\nProcessing batch ${
            Math.floor(i / this.BATCH_SIZE) + 1
          }, wallets ${i} to ${i + batch.length}`
        );
        await this.processBatch(batch);
      }
 
      console.log("\nAll wallets processed. Starting countdown...");
      await countdown(CONFIG.PING_INTERVAL * 60); // Convert minutes to seconds
    }
  }
}
 
// Start the dashboard
const dashboard = new WalletDashboard();
dashboard.start().catch((error) => {
  console.error(`${colors.error}Fatal error: ${error}${colors.reset}`);
  process.exit(1);
});