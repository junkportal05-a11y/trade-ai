import logging
from typing import List

logger = logging.getLogger("SurvivorshipValidator")

class SurvivorshipValidator:
    """
    Ensures that historical backtests do not suffer from survivorship bias by 
    validating that the tested universe includes stocks that were removed, 
    delisted, or went bankrupt during the test period.
    """
    
    # A known list of high-profile Indian stocks that were removed from F&O, 
    # crashed, or delisted over the last 10 years.
    KNOWN_FAILURES = {
        "DHFL.NS", "RELCAPITAL.NS", "YESBANK.NS", "IDEA.NS", 
        "RCOM.NS", "JAINIRRIG.NS", "PCJEWELLER.NS", "SUZLON.NS",
        "HDIL.NS", "JPASSOCIAT.NS", "UNITECH.NS", "GMRINFRA.NS",
        "IBULLHSGFIN.NS"
    }

    def __init__(self, target_failure_ratio: float = 0.05):
        """
        target_failure_ratio: The minimum percentage of the universe that must 
                              consist of known historical failures to pass validation.
        """
        self.target_failure_ratio = target_failure_ratio

    def validate_universe(self, universe: List[str]) -> dict:
        """
        Validates the testing universe against known historical failures.
        Returns a dict with validation status.
        """
        universe_set = set(universe)
        included_failures = universe_set.intersection(self.KNOWN_FAILURES)
        
        failure_ratio = len(included_failures) / len(universe) if universe else 0.0
        passed = failure_ratio >= self.target_failure_ratio
        
        if not passed:
            logger.warning(
                f"SURVIVORSHIP BIAS DETECTED! Your universe of {len(universe)} stocks "
                f"only includes {len(included_failures)} historical failures "
                f"({failure_ratio:.1%}). Target is {self.target_failure_ratio:.1%}."
            )
            logger.warning(
                "You are testing only on stocks that survived. Your backtest "
                "results will be artificially inflated. Add historical F&O components."
            )
        else:
            logger.info("Survivorship Bias check passed. Universe contains historical failures.")

        return {
            "passed": passed,
            "universe_size": len(universe),
            "included_failures": list(included_failures),
            "failure_ratio": failure_ratio,
            "target_ratio": self.target_failure_ratio
        }

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    validator = SurvivorshipValidator()
    
    # Test with a biased universe
    biased_universe = ["RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS"]
    validator.validate_universe(biased_universe)
    
    # Test with an unbiased universe
    unbiased_universe = ["RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "DHFL.NS", "YESBANK.NS"]
    validator.validate_universe(unbiased_universe)
