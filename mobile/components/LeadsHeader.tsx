import React from "react";
import { StyleSheet, Text, View } from "react-native";
import ConnectionState from "./ConnectionState";

interface LeadsHeaderProps {
  count: number;
  connected: boolean;
  error?: string;
}

export default function LeadsHeader({ count, connected, error }: LeadsHeaderProps) {
  return (
    <View style={styles.container}>
      <Text style={styles.title}>Leads</Text>
      <Text style={styles.summary}>
        {count} {count === 1 ? "Lead" : "Leads"}
      </Text>
      <ConnectionState connected={connected} message={error} />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    paddingTop: 8,
    paddingBottom: 16,
  },
  title: {
    fontSize: 28,
    fontWeight: "700",
    color: "#111827",
  },
  summary: {
    marginTop: 2,
    fontSize: 14,
    color: "#6B7280",
  },
});
