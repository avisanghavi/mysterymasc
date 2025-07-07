# HeyJarvis Documentation

Welcome to the HeyJarvis documentation! This directory contains comprehensive guides for migrating to and using Jarvis business orchestration.

## 📚 Documentation Overview

### [MIGRATION_TO_JARVIS.md](./MIGRATION_TO_JARVIS.md)
**Complete migration guide** from agent builder to Jarvis business orchestration.

**Contents:**
- Overview of changes and benefits
- Step-by-step migration path
- Code examples for conversion
- Parallel operation guide
- Configuration setup
- Troubleshooting common issues

**Who should read this:** Existing HeyJarvis users, developers planning migration

### [QUICK_REFERENCE.md](./QUICK_REFERENCE.md)
**Quick reference guide** for developers working with both systems.

**Contents:**
- Command line usage
- Key code patterns
- When to use which system
- Common troubleshooting fixes
- Environment variables

**Who should read this:** Developers, technical users needing quick answers

## 🚀 Getting Started

### New Users
1. Start with the main [README.md](../README.md) in the project root
2. Try the demo modes: `python3 main.py --demo`
3. Review this migration guide when ready to use business features

### Existing Users
1. **Read [MIGRATION_TO_JARVIS.md](./MIGRATION_TO_JARVIS.md)** - Your existing workflows remain unchanged
2. **Try Jarvis mode:** `python3 main.py --jarvis`
3. **Use [QUICK_REFERENCE.md](./QUICK_REFERENCE.md)** for daily development

### Developers
1. Review the migration guide for integration patterns
2. Use the quick reference for common code patterns
3. Run `python3 test_migration_examples.py` to validate setup

## 🔧 Key Concepts

### Dual System Operation
- **Agent Builder**: Individual technical automation (existing)
- **Jarvis**: Business-level orchestration (new)
- **Both systems coexist** without conflicts

### Migration Philosophy
- **Zero breaking changes** to existing functionality
- **Gradual adoption** of business features
- **Parallel operation** during transition
- **Complete backward compatibility**

### When to Use What

| Use Agent Builder For | Use Jarvis For |
|----------------------|----------------|
| Technical automation | Business goals |
| Custom integrations | Department coordination |
| Individual agents | Strategic outcomes |
| Specific tools | Process optimization |

## 📋 Migration Checklist

- [ ] Read migration guide completely
- [ ] Test existing workflows still work
- [ ] Try demo modes (options 6-7 for Jarvis)
- [ ] Set up Jarvis configuration
- [ ] Test parallel operation
- [ ] Migrate one business process
- [ ] Validate WebSocket integration
- [ ] Update team documentation

## 🔍 Quick Commands

```bash
# Test current setup
python3 main.py

# Try Jarvis business mode
python3 main.py --jarvis

# Interactive demos (try options 6-7)
python3 main.py --demo

# Validate migration guide examples
python3 test_migration_examples.py

# Run integration tests
python3 run_integration_tests.py
```

## 🆘 Getting Help

### Common Issues
- **Import errors**: Check [MIGRATION_TO_JARVIS.md](./MIGRATION_TO_JARVIS.md) troubleshooting section
- **Configuration conflicts**: Use separate namespaces (see guide)
- **Session overlaps**: Use prefixed session IDs
- **Performance issues**: Implement resource management

### Support Resources
1. **Troubleshooting section** in migration guide
2. **Code examples** with working patterns
3. **Test scripts** to validate setup
4. **Demo modes** for hands-on learning

### Validation Tools
- `test_migration_examples.py` - Validates guide examples
- `run_integration_tests.py` - Full integration testing
- `test_jarvis_demos.py` - Demo functionality testing

## 📈 Migration Success Metrics

Track these to measure migration success:
- ✅ Existing workflows continue working
- ✅ Business requests process correctly
- ✅ Department coordination functions
- ✅ WebSocket updates working
- ✅ Performance maintained or improved
- ✅ Team adoption and satisfaction

## 🔮 Future Roadmap

### Planned Enhancements
- Unified interface for both systems
- Intelligent request routing
- Additional department templates
- Advanced business analytics
- Enterprise integration features

### Migration Path Evolution
- **Current**: Parallel operation
- **Next**: Unified interface
- **Future**: Intelligent routing
- **Long-term**: Full business orchestration

## 📞 Contributing

Found issues with the migration guide? Want to improve documentation?

1. Test your changes with validation scripts
2. Update both migration guide and quick reference
3. Ensure backward compatibility
4. Add examples for new patterns

---

**Remember**: Your existing HeyJarvis workflows continue working unchanged. Jarvis adds business capabilities on top of the solid foundation you already know and use.