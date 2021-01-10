# Time in milliseconds that the monte carlo matcher can take to generate pairs.
MATCHER_MONTECARLO_TIMEOUT_MS = 1000

# The percentile, at or below which the weight is considered good (green). This is used for evaluation of matches.
# Allowed values: [0, 100]
MATCHER_GREEN_PERCENTILE = 33.3

# The percentile, at or below which the weight is considered average (yello). This is used for evaluation of matches.
# Allowed values: [0, 100]
MATCHER_YELLOW_PERCENTILE = 66.6
