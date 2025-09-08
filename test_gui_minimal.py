#!/usr/bin/env python3
"""
Minimal GUI test to isolate the Tkinter issue
"""
import os
import sys

# Set environment variables to fix macOS issues
os.environ["TK_SILENCE_DEPRECATION"] = "1"

def test_basic_tkinter():
    """Test if basic Tkinter works"""
    print("🔍 Testing basic Tkinter...")
    
    try:
        import tkinter as tk
        print("✅ Tkinter import successful")
        
        root = tk.Tk()
        root.title("Test Window")
        root.geometry("300x200")
        
        label = tk.Label(root, text="Test GUI Window")
        label.pack(pady=50)
        
        print("✅ Tkinter window created")
        
        # Show window briefly
        root.update()
        root.after(2000, root.quit)  # Close after 2 seconds
        root.mainloop()
        
        print("✅ Basic Tkinter test passed")
        return True
        
    except Exception as e:
        print(f"❌ Basic Tkinter failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_gui_imports():
    """Test if GUI imports work without creating windows"""
    print("\n🔍 Testing GUI imports...")
    
    try:
        from parrot.state import State
        from parrot.director.director import Director
        from parrot.director.signal_states import SignalStates
        print("✅ Core imports successful")
        
        # Test GUI import without creating window
        from parrot.gui.gui import Window
        print("✅ GUI module import successful")
        
        return True
        
    except Exception as e:
        print(f"❌ GUI imports failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_gui_window_creation():
    """Test GUI window creation with minimal setup"""
    print("\n🔍 Testing GUI window creation...")
    
    try:
        from parrot.state import State
        from parrot.director.director import Director
        from parrot.director.signal_states import SignalStates
        from parrot.gui.gui import Window
        
        # Create minimal components
        state = State()
        signal_states = SignalStates()
        
        print("✅ Creating Director...")
        director = Director(state)
        print("✅ Director created")
        
        print("✅ Creating GUI Window...")
        window = Window(state, lambda: None, director, signal_states)
        print("✅ GUI Window created successfully!")
        
        # Test window display
        window.update()
        window.after(3000, window.quit)  # Close after 3 seconds
        
        print("✅ Starting window mainloop...")
        window.mainloop()
        
        print("✅ GUI window test passed!")
        return True
        
    except Exception as e:
        print(f"❌ GUI window creation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run GUI tests"""
    print("🖥️" * 50)
    print("  GUI DIAGNOSTIC TESTS")
    print("🖥️" * 50)
    
    # Test 1: Basic Tkinter
    if not test_basic_tkinter():
        print("\n❌ Basic Tkinter failed - macOS compatibility issue")
        return False
    
    # Test 2: GUI imports
    if not test_gui_imports():
        print("\n❌ GUI imports failed - module issue")
        return False
    
    # Test 3: GUI window creation
    if not test_gui_window_creation():
        print("\n❌ GUI window creation failed - Party Parrot GUI issue")
        return False
    
    print("\n" + "✅" * 50)
    print("  ALL GUI TESTS PASSED!")
    print("✅" * 50)
    
    print("\n🏆 GUI System Status:")
    print("   ✅ Basic Tkinter working")
    print("   ✅ Party Parrot GUI imports working")
    print("   ✅ Window creation successful")
    print("   ✅ Ready for full application!")
    
    return True

if __name__ == "__main__":
    success = main()
    if success:
        print("\n🚀 GUI is working - ready to test full application!")
    else:
        print("\n⚠️ GUI issues detected - need further fixes")
    sys.exit(0 if success else 1)
