class FuzzyCore:
    def __init__(self, input_sets, output_sets, rules, output_ranges):
        """
        input_sets: dict.
        output_sets: dict.
        rules: list of dict.
        output_ranges: dict; crisp output ranges
        """
        self.input_sets = input_sets
        self.output_sets = output_sets
        self.rules = rules
        self.output_ranges = output_ranges

    # ---------- Fuzzification ----------
    def fuzzify(self, inputs):
        """
        inputs: {"distance": 120, "temp": 30, etc}
        returns: {"distance": {"close": 0.2, ...}, "temp": {...}}
        """
        fuzzified = {}
        try:
            for var_name, value in inputs.items():
                # Ensure variable exists in config.
                if var_name not in self.input_sets:
                    print("Unknown input variable in fuzzify:", var_name)
                    continue

                # Handle missing input values.
                if value is None:
                    fuzzified[var_name] = {label: 0.0 for label in self.input_sets[var_name]}
                    continue

                # Apply membership functions safely.
                sets = self.input_sets[var_name]
                fuzzified[var_name] = {}
                for label, fn in sets.items():
                    try:
                        fuzzified[var_name][label] = fn(value)
                    except Exception as e:
                        print(f"Fuzzify error on {var_name}-{label}:", e)
                        fuzzified[var_name][label] = 0.0
        except Exception as e:
            print("Fuzzify stage error:", e)
        return fuzzified

    # ---------- Apply Rules ----------
    def apply_rules(self, fuzzified):
        """
        Returns activations for each output variable's fuzzy sets
        Example: {"pwm": {"high": 0.7, "low": 0.2}, "servo": {"left": 0.5}}
        """
        try:
            # Initialize all outputs with 0 activation.
            activations = {out: {label: 0.0 for label in sets}
                           for out, sets in self.output_sets.items()}

            # Evaluate each rule.
            for rule in self.rules:
                conditions = rule.get("if", {})
                try:
                    values = [fuzzified[var][label] for var, label in conditions.items()]
                except KeyError as e:
                    print("Missing fuzzified value in rule:", e)
                    continue

                rule_strength = min(values) if values else 0.0

                # Apply to all outputs defined in "then".
                for out_var, out_label in rule.get("then", {}).items():
                    if out_var in activations and out_label in activations[out_var]:
                        activations[out_var][out_label] = max(
                            activations[out_var][out_label], rule_strength
                        )

            return activations

        except Exception as e:
            print("Apply rules error:", e)
            # Return zero activation if failure.
            return {out: {label: 0.0 for label in sets}
                    for out, sets in self.output_sets.items()}

    # ---------- Aggregate + Defuzzify ----------
    def aggregate_and_defuzzify(self, activations):
        """
        For each output variable:
          - Build aggregated membership across domain.
          - Defuzzify via centroid.
        Returns crisp outputs: {"pwm": value, "servo": value}.
        """
        crisp_outputs = {}
        try:
            for out_var, sets in self.output_sets.items():
                out_min, out_max = self.output_ranges[out_var]
                step = 1 if out_var == 'duty' else 10
                domain = list(range(out_min, out_max + 1, step))

                aggregated = []
                for x in domain:
                    # For each label in this output variable.
                    memberships = []
                    for label, fn in sets.items():
                        try:
                            memberships.append(min(activations[out_var][label], fn(x)))
                        except Exception as e:
                            print(f"Defuzzify membership error on {out_var}-{label}:", e)
                            memberships.append(0.0)
                    aggregated.append(max(memberships))

                # Defuzzify centroid.
                numerator = sum(x * mu for x, mu in zip(domain, aggregated))
                denominator = sum(aggregated) or 1.0
                crisp_outputs[out_var] = numerator / denominator

        except Exception as e:
            print("Defuzzify stage error:", e)
            # Safe fallback to minimum ranges.
            crisp_outputs = {out_var: self.output_ranges[out_var][0] for out_var in self.output_sets}

        return crisp_outputs

    # ---------- Full Pipeline ----------
    def compute(self, inputs):
        try:
            fuzzified = self.fuzzify(inputs)
            activations = self.apply_rules(fuzzified)

            # If no rules fired, return minimum safe outputs.
            if all(all(val == 0 for val in out.values()) for out in activations.values()):
                return {out_var: self.output_ranges[out_var][0] for out_var in self.output_sets}

            return self.aggregate_and_defuzzify(activations)

        except Exception as e:
            print("Compute pipeline error:", e)
            # Return safe fallback values.
            return {out_var: self.output_ranges[out_var][0] for out_var in self.output_sets}
