module.exports = function override(config, env) {
  // Ignore source map warnings for powerbi-client
  config.ignoreWarnings = [
    ...(config.ignoreWarnings || []),
    /Failed to parse source map/,
    /source-map-loader/,
    /powerbi-client/,
  ];

  // Add rule to exclude powerbi-client from source-map-loader
  config.module.rules = config.module.rules.map(rule => {
    if (rule.enforce === 'pre' && rule.use && rule.use.some(u => u.loader && u.loader.includes('source-map-loader'))) {
      return {
        ...rule,
        exclude: /node_modules\/powerbi-client/
      };
    }
    return rule;
  });

  return config;
};