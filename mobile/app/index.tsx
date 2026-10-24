import React, { useEffect, useState } from "react";
import { FlatList, StyleSheet, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import EmptyState from "../components/EmptyState";
import LeadCard from "../components/LeadCard";
import LeadsHeader from "../components/LeadsHeader";
import LoginForm from "../components/LoginForm";
import LoadingState from "../components/LoadingState";
import { connectToLeadUpdates, fetchLeads, login, UnauthorizedError } from "../services/leads";
import { Lead } from "../types/lead";

export default function LeadsScreen() {
  const [leads, setLeads] = useState<Lead[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | undefined>();
  const [accessToken, setAccessToken] = useState<string>();
  const [loginError, setLoginError] = useState<string | undefined>();
  const [isLoggingIn, setIsLoggingIn] = useState(false);

  useEffect(() => {
    if (!accessToken) return;
    let active = true;
    let authorized = true;
    let disconnect = () => {};

    fetchLeads(accessToken)
      .then((storedLeads) => {
        if (!active) return;
        setLeads(storedLeads);
      }).catch((fetchError: unknown) => {
        if (!active) return;
        if (fetchError instanceof UnauthorizedError) {
          authorized = false;
          setAccessToken(undefined);
          setLoginError("Please sign in again.");
        } else {
          setError("Backend unavailable");
        }
      })
      .finally(() => {
        if (!active || !authorized) return;
        setIsLoading(false);
        disconnect = connectToLeadUpdates(
          accessToken,
          (lead) => {
            setLeads((current) => [lead, ...current.filter((item) => item.id !== lead.id)]);
          },
          (connected) => {
            setIsConnected(connected);
            if (connected) {
              setError(undefined);
              fetchLeads(accessToken).then((latestLeads) => {
                if (!active) return;
                setLeads((current) => {
                  const byId = new Map(current.map((lead) => [lead.id, lead]));
                  latestLeads.forEach((lead) => byId.set(lead.id, lead));
                  return Array.from(byId.values());
                });
              }).catch((fetchError: unknown) => {
                if (!active) return;
                if (fetchError instanceof UnauthorizedError) {
                  setAccessToken(undefined);
                  setLoginError("Please sign in again.");
                } else {
                  setError("Backend API unavailable");
                }
              });
            } else {
              setError("Live connection interrupted · reconnecting");
            }
          },
          () => {
            if (!active) return;
            setAccessToken(undefined);
            setLoginError("Please sign in again.");
          },
        );
      });

    return () => {
      active = false;
      disconnect();
    };
  }, [accessToken]);

  const handleLogin = async (email: string, password: string) => {
    setIsLoggingIn(true);
    setLoginError(undefined);
    try {
      setAccessToken(await login(email, password));
      setLeads([]);
      setIsLoading(true);
    } catch (loginFailure) {
      setLoginError(loginFailure instanceof Error ? loginFailure.message : "Sign in failed");
    } finally {
      setIsLoggingIn(false);
    }
  };

  if (!accessToken) {
    return <LoginForm error={loginError} isLoading={isLoggingIn} onLogin={handleLogin} />;
  }

  return (
    <SafeAreaView style={styles.safeArea}>
      {isLoading ? <LoadingState /> : (
        <FlatList
          data={leads}
          keyExtractor={(item) => item.id}
          renderItem={({ item }) => <LeadCard lead={item} />}
          ListHeaderComponent={
            <LeadsHeader
              count={leads.length}
              connected={isConnected}
              error={error}
              onSignOut={() => {
                setAccessToken(undefined);
                setLeads([]);
                setError(undefined);
                setLoginError(undefined);
                setIsConnected(false);
              }}
            />
          }
          ListEmptyComponent={<EmptyState />}
          contentContainerStyle={styles.listContent}
          showsVerticalScrollIndicator={false}
          ListFooterComponent={error ? (
            <View style={styles.errorBox}>
              <Text style={styles.errorText}>{error}. Confirm the backend URL and that FastAPI is running.</Text>
            </View>
          ) : null}
        />
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: "#F9FAFB",
  },
  listContent: {
    flexGrow: 1,
    paddingHorizontal: 16,
    paddingBottom: 24,
  },
  errorBox: {
    paddingVertical: 12,
  },
  errorText: {
    color: "#9A4D28",
    fontSize: 13,
    textAlign: "center",
  },
});
