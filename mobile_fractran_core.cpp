#include <cstdint>
#include <exception>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
#include <vector>

struct Fraction {
    std::uint64_t numerator;
    std::uint64_t denominator;
};

bool apply_rule(std::uint64_t &state, const Fraction &rule) {
    if (state % rule.denominator != 0) {
        return false;
    }

    const std::uint64_t quotient = state / rule.denominator;
    if (quotient > std::numeric_limits<std::uint64_t>::max() / rule.numerator) {
        throw std::overflow_error("FRACTRAN state overflow");
    }

    state = quotient * rule.numerator;
    return true;
}

int main(int argc, char **argv) {
    std::uint64_t state = 2;
    if (argc == 2) {
        try {
            state = std::stoull(argv[1]);
        } catch (const std::exception &error) {
            std::cerr << "Invalid starting state: " << error.what() << '\n';
            return 2;
        }
    } else if (argc > 2) {
        std::cerr << "Usage: " << argv[0] << " [positive-integer-state]\n";
        return 2;
    }

    const std::vector<Fraction> rules = {{3, 2}, {5, 3}, {1, 5}};
    constexpr std::size_t max_steps = 1000;
    std::size_t steps = 0;

    try {
        while (steps < max_steps) {
            bool applied = false;
            for (const Fraction &rule : rules) {
                if (apply_rule(state, rule)) {
                    applied = true;
                    ++steps;
                    break;
                }
            }
            if (!applied) {
                break;
            }
        }
    } catch (const std::exception &error) {
        std::cerr << "FRACTRAN execution failed: " << error.what() << '\n';
        return 1;
    }

    std::cout << "state=" << state << " steps=" << steps << '\n';
    return steps == max_steps ? 1 : 0;
}
