import math
import pytest

def main():
    """
    The main function prompts the user for the cylinder's measurements
    and prints the calculated area and volume.
    """
    print("This program computes the area of a circle and the volume of a cylinder.")

    # Get user input for the radius and height
    radius = float(input("Please enter the radius of the cylinder's radius (cm): "))
    height = float(input("Please enter the cylinder's height (cm): "))

    # 1. Compute the area of the circle base
    area = circle_area(radius)

    # 2. Compute the volume of the cylinder
    volume = cylinder_volume(area, height)

    # Print the results
    print(f"\nThe area of the circular base is {area:.2f} square centimeters.")
    print(f"The volume of the cylinder is {volume:.2f} cubic centimeters.")


def circle_area(radius):
    """
    Calculates the area of a circle using the formula: area = π * radius²
    
    Parameters:
        radius (float): The radius of the circle.
    Returns:
        float: The area of the circle.
    """
    area = math.pi * radius**2
    return area


def cylinder_volume(area, height):
    """
    Calculates the volume of a cylinder using the formula: volume = area * height
    
    Parameters:
        area (float): The area of the circular base.
        height (float): The height of the cylinder.
    Returns:
        float: The volume of the cylinder.
    """
    volume = area * height
    return volume


# --------------------------------------------------------------------------
# The code below tests the functions to satisfy the "Testing and Fixing" requirement.
# --------------------------------------------------------------------------

def test_circle_area():
    """Tests the circle_area function with known values."""
    # Test case 1: Radius 0
    assert circle_area(0) == 0

    # Test case 2: Radius 1
    # Expected area: pi * 1^2 = 3.14159...
    assert abs(circle_area(1) - 3.1415926535) < 1e-10

    # Test case 3: Radius 5 (Using the math.pi constant directly for accuracy)
    # Expected area: pi * 5^2 = 78.5398...
    expected_area = math.pi * 5**2
    assert abs(circle_area(5) - expected_area) < 1e-10


def test_cylinder_volume():
    """Tests the cylinder_volume function with known values."""
    # Test case 1: Zero area or zero height
    assert cylinder_volume(10, 0) == 0
    assert cylinder_volume(0, 10) == 0

    # Test case 2: Area 10, Height 5
    # Expected volume: 10 * 5 = 50
    assert cylinder_volume(10, 5) == 50

    # Test case 3: Area 78.54, Height 10
    # Expected volume: 78.54 * 10 = 785.4
    assert abs(cylinder_volume(78.54, 10) - 785.4) < 1e-10


# Call main to start the program
if __name__ == "__main__":
    # The functions will run when you execute this script normally.
    main()

    # The tests should be run separately (e.g., using the pytest command)
    # or by uncommenting and running them, if instructed.
    
    # You can manually run the tests by uncommenting these:
    # test_circle_area()
    # test_cylinder_volume()
    # print("\nAll functions passed manual testing!")