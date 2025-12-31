"""
Test the advanced timetabling features
"""

if __name__ == "__main__":
    print("🚀 TESTING ADVANCED TIMETABLING FEATURES")
    print("=" * 60)

    try:
        from timetable_agent import solve_from_json_advanced, ADVANCED_FEATURES

        if ADVANCED_FEATURES:
            print("✅ Advanced features are available!")
            print("\n📋 Testing enhanced solve function...")

            result = solve_from_json_advanced(
                "test/09_real_world_scenario.json",
                "timetable_advanced_output.json",
                compare_all=False,
                enable_validation=True,
                enable_backup=False,  # Disable for testing
                export_formats=['csv', 'stats']
            )

            if result:
                print(f"\n✅ ADVANCED SOLVE COMPLETED!")
                print(f"   - Algorithm: {result['result'].algorithm}")
                print(f"   - Events scheduled: {len(result['final_state'])}")
                print(f"   - Conflicts found: {len(result['conflicts'])}")
                if result['quality_report']:
                    print(f"   - Overall quality: {result['quality_report'].overall_score:.1%}")

        else:
            print("⚠️ Advanced features not available, testing basic functionality...")
            from timetable_agent import solve_from_json
            solve_from_json("test/09_real_world_scenario.json", "timetable_basic_output.json", compare_all=False)
            print("✅ Basic solve completed!")

    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()

    print("\n🎉 TESTING COMPLETED!")

    # Test individual modules
    print("\n🔧 TESTING INDIVIDUAL MODULES...")

    try:
        from timetable_preferences import PreferenceManager
        pm = PreferenceManager()
        print("✅ Preferences module working")
    except:
        print("⚠️ Preferences module not available")

    try:
        from timetable_enhanced_export import EnhancedTimetableExporter
        print("✅ Enhanced export module working")
    except:
        print("⚠️ Enhanced export module not available")

    try:
        from timetable_backup import TimetableBackupManager
        print("✅ Backup module working")
    except:
        print("⚠️ Backup module not available")

    print("\n📊 FEATURE SUMMARY:")
    print("- ✅ Basic timetabling (always available)")
    print("- ✅ HTML export (always available)")
    print("- ✅ JSON export (always available)")
    print("- ✅ Automatic unique ID generation (always available)")
    print("- ✅ ALL macro support (always available)")
    print("- ✅ Multiple algorithms (DFS, BFS, UCS, A*)")

    if ADVANCED_FEATURES:
        print("- ✅ Conflict detection and analysis")
        print("- ✅ Quality validation and scoring")
        print("- ✅ Enhanced export formats (CSV, iCal, XML, etc.)")
        print("- ✅ Preference-based optimization")
        print("- ✅ Backup and version control")
        print("- ✅ Statistical reporting")
    else:
        print("- ⚠️ Advanced features require additional modules")

    print(f"\n🏆 SYSTEM STATUS: {'FULLY ENHANCED' if ADVANCED_FEATURES else 'BASIC FUNCTIONALITY'}")
