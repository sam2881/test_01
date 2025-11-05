"""
Sample Calculator Module
A simple calculator with basic arithmetic operations for testing purposes
"""


class Calculator:
    """A simple calculator class with basic arithmetic operations"""

    def __init__(self):
        """Initialize calculator with history tracking"""
        self.history = []

    def add(self, a: float, b: float) -> float:
        """
        Add two numbers

        Args:
            a: First number
            b: Second number

        Returns:
            Sum of a and b
        """
        result = a + b
        self.history.append(f"add({a}, {b}) = {result}")
        return result

    def subtract(self, a: float, b: float) -> float:
        """
        Subtract b from a

        Args:
            a: Number to subtract from
            b: Number to subtract

        Returns:
            Difference of a and b
        """
        result = a - b
        self.history.append(f"subtract({a}, {b}) = {result}")
        return result

    def multiply(self, a: float, b: float) -> float:
        """
        Multiply two numbers

        Args:
            a: First number
            b: Second number

        Returns:
            Product of a and b
        """
        result = a * b
        self.history.append(f"multiply({a}, {b}) = {result}")
        return result

    def divide(self, a: float, b: float) -> float:
        """
        Divide a by b

        Args:
            a: Dividend
            b: Divisor

        Returns:
            Quotient of a and b

        Raises:
            ValueError: If b is zero
        """
        if b == 0:
            raise ValueError("Cannot divide by zero")

        result = a / b
        self.history.append(f"divide({a}, {b}) = {result}")
        return result

    def power(self, base: float, exponent: float) -> float:
        """
        Raise base to the power of exponent

        Args:
            base: The base number
            exponent: The exponent

        Returns:
            base raised to exponent
        """
        result = base ** exponent
        self.history.append(f"power({base}, {exponent}) = {result}")
        return result

    def square_root(self, n: float) -> float:
        """
        Calculate square root of n

        Args:
            n: Number to find square root of

        Returns:
            Square root of n

        Raises:
            ValueError: If n is negative
        """
        if n < 0:
            raise ValueError("Cannot calculate square root of negative number")

        result = n ** 0.5
        self.history.append(f"square_root({n}) = {result}")
        return result

    def clear_history(self):
        """Clear calculation history"""
        self.history = []

    def get_history(self) -> list:
        """
        Get calculation history

        Returns:
            List of calculation history strings
        """
        return self.history.copy()


def calculate_average(numbers: list) -> float:
    """
    Calculate average of a list of numbers

    Args:
        numbers: List of numbers

    Returns:
        Average of the numbers

    Raises:
        ValueError: If list is empty
    """
    if not numbers:
        raise ValueError("Cannot calculate average of empty list")

    return sum(numbers) / len(numbers)


def calculate_percentage(value: float, total: float) -> float:
    """
    Calculate percentage of value relative to total

    Args:
        value: The value
        total: The total amount

    Returns:
        Percentage (0-100)

    Raises:
        ValueError: If total is zero
    """
    if total == 0:
        raise ValueError("Total cannot be zero")

    return (value / total) * 100


if __name__ == "__main__":
    # Demo usage
    calc = Calculator()

    print("Calculator Demo")
    print("=" * 40)

    print(f"5 + 3 = {calc.add(5, 3)}")
    print(f"10 - 4 = {calc.subtract(10, 4)}")
    print(f"6 * 7 = {calc.multiply(6, 7)}")
    print(f"20 / 4 = {calc.divide(20, 4)}")
    print(f"2^8 = {calc.power(2, 8)}")
    print(f"√16 = {calc.square_root(16)}")

    print("\nHistory:")
    for entry in calc.get_history():
        print(f"  {entry}")

    print("\nUtility Functions:")
    numbers = [10, 20, 30, 40, 50]
    print(f"Average of {numbers} = {calculate_average(numbers)}")
    print(f"25 is {calculate_percentage(25, 100)}% of 100")
