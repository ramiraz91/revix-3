// craco.config.js
const path = require("path");
require("dotenv").config();

// Check if we're in development/preview mode (not production build)
// Craco sets NODE_ENV=development for start, NODE_ENV=production for build
const isDevServer = process.env.NODE_ENV !== "production";

// Environment variable overrides
const config = {
  enableHealthCheck: process.env.ENABLE_HEALTH_CHECK === "true",
  enableVisualEdits: isDevServer, // Only enable during dev server
};

// Conditionally load visual edits modules only in dev mode
let setupDevServer;
let babelMetadataPlugin;

if (config.enableVisualEdits) {
  setupDevServer = require("./plugins/visual-edits/dev-server-setup");
  babelMetadataPlugin = require("./plugins/visual-edits/babel-metadata-plugin");
}

// Conditionally load health check modules only if enabled
let WebpackHealthPlugin;
let setupHealthEndpoints;
let healthPluginInstance;

if (config.enableHealthCheck) {
  WebpackHealthPlugin = require("./plugins/health-check/webpack-health-plugin");
  setupHealthEndpoints = require("./plugins/health-check/health-endpoints");
  healthPluginInstance = new WebpackHealthPlugin();
}

const webpackConfig = {
  eslint: {
    configure: {
      extends: ["plugin:react-hooks/recommended"],
      rules: {
        "react-hooks/rules-of-hooks": "error",
        "react-hooks/exhaustive-deps": "warn",
      },
    },
  },
  webpack: {
    alias: {
      '@': path.resolve(__dirname, 'src'),
    },
    configure: (webpackConfig) => {

      // Add ignored patterns to reduce watched directories
        webpackConfig.watchOptions = {
          ...webpackConfig.watchOptions,
          ignored: [
            '**/node_modules/**',
            '**/.git/**',
            '**/build/**',
            '**/dist/**',
            '**/coverage/**',
            '**/public/**',
        ],
      };

      // Add health check plugin to webpack if enabled
      if (config.enableHealthCheck && healthPluginInstance) {
        webpackConfig.plugins.push(healthPluginInstance);
      }
      return webpackConfig;
    },
  },
};

// Only add babel metadata plugin during dev server
if (config.enableVisualEdits && babelMetadataPlugin) {
  const problematicFiles = ['Layout.jsx', 'Liquidaciones.jsx', 'OrdenesCompra.jsx'];

  const safePlugin = (api, options, dirname) => {
    let original;
    try {
      original = typeof babelMetadataPlugin === 'function'
        ? babelMetadataPlugin(api, options, dirname)
        : babelMetadataPlugin;
    } catch(e) {
      return { visitor: {} };
    }

    const visitor = original && original.visitor ? original.visitor : (original || {});
    const safeVisitor = {};

    for (const key of Object.keys(visitor)) {
      const fn = visitor[key];
      if (typeof fn !== 'function') {
        safeVisitor[key] = fn;
        continue;
      }
      safeVisitor[key] = function(nodePath, state) {
        try {
          const filename = (state && state.filename) || (this && this.filename) || '';
          if (problematicFiles.some(f => filename.includes(f))) return;
          return fn.call(this, nodePath, state);
        } catch(e) {
          // silently skip files that cause plugin errors
        }
      };
    }

    return { ...(original || {}), visitor: safeVisitor };
  };

  webpackConfig.babel = {
    plugins: [safePlugin],
  };
}

webpackConfig.devServer = (devServerConfig) => {
  // Disable error overlay to prevent blocking UI with plugin-level errors
  devServerConfig.client = {
    ...devServerConfig.client,
    overlay: false,
  };

  // Apply visual edits dev server setup only if enabled
  if (config.enableVisualEdits && setupDevServer) {
    devServerConfig = setupDevServer(devServerConfig);
  }

  // Add health check endpoints if enabled
  if (config.enableHealthCheck && setupHealthEndpoints && healthPluginInstance) {
    const originalSetupMiddlewares = devServerConfig.setupMiddlewares;

    devServerConfig.setupMiddlewares = (middlewares, devServer) => {
      // Call original setup if exists
      if (originalSetupMiddlewares) {
        middlewares = originalSetupMiddlewares(middlewares, devServer);
      }

      // Setup health endpoints
      setupHealthEndpoints(devServer, healthPluginInstance);

      return middlewares;
    };
  }

  return devServerConfig;
};

module.exports = webpackConfig;
