#!/usr/bin/env python3
"""
Test GUI without pygame to see if there's a conflict
"""
import os

# Set environment for macOS
os.environ["TK_SILENCE_DEPRECATION"] = "1"

def test_gui_without_pygame():
    """Test GUI creation without importing pygame"""
    print("🔍 Testing GUI without pygame...")
    
    try:
        # Import everything EXCEPT pygame-related modules
        from parrot.state import State
        from parrot.director.signal_states import SignalStates
        
        print("✅ Core imports successful (no pygame)")
        
        # Import GUI
        from parrot.gui.gui import Window
        print("✅ GUI import successful")
        
        # Create minimal components
        state = State()
        signal_states = SignalStates()
        
        print("✅ Creating Director without VJ...")
        # Import Director but don't create VJ system
        from parrot.director.director import Director
        director = Director(state)
        print("✅ Director created")
        
        print("✅ Creating GUI Window...")
        window = Window(state, lambda: window.quit(), director, signal_states)
        print("✅ GUI Window created!")
        
        # Show window
        window.geometry("800x600")
        window.update()
        
        print("✅ Window displayed - checking if visible...")
        window.after(3000, window.quit)
        window.mainloop()
        
        print("✅ GUI test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ GUI test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_pygame_conflict():
    """Test if pygame import affects Tkinter"""
    print("\n🔍 Testing pygame + Tkinter conflict...")
    
    try:
        # Import pygame first
        import pygame
        print("✅ Pygame imported")
        
        # Then try Tkinter
        import tkinter as tk
        print("✅ Tkinter imported after pygame")
        
        # Create window
        root = tk.Tk()
        root.title("Pygame + Tkinter Test")
        root.geometry("400x300")
        
        label = tk.Label(root, text="Pygame + Tkinter Working")
        label.pack(pady=50)
        
        root.update()
        root.after(2000, root.quit)
        root.mainloop()
        
        print("✅ Pygame + Tkinter test passed")
        return True
        
    except Exception as e:
        print(f"❌ Pygame + Tkinter conflict: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run GUI conflict tests"""
    print("🔍" * 40)
    print("  GUI CONFLICT DIAGNOSIS")
    print("🔍" * 40)
    
    # Test without pygame
    if not test_gui_without_pygame():
        print("❌ GUI fails even without pygame")
        return False
    
    # Test pygame conflict
    if not test_pygame_conflict():
        print("❌ Pygame conflicts with Tkinter")
        return False
    
    print("\n✅ No pygame/GUI conflicts detected")
    print("🔍 Issue must be elsewhere in the application")
    
    return True

if __name__ == "__main__":
    main()
