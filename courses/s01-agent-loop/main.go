/*
s01_agent_loop.py - The Agent Loop

The entire secret of an AI coding agent in one pattern:

	while stop_reason == "tool_use":
	    response = LLM(messages, tools)
	    execute tools
	    append results

	+----------+      +-------+      +---------+
	|   User   | ---> |  LLM  | ---> |  Tool   |
	|  prompt  |      |       |      | execute |
	+----------+      +---+---+      +----+----+
	                      ^               |
	                      |   tool_result |
	                      +---------------+
	                      (loop continues)

This is the core loop: feed tool results back to the model
until the model decides to stop. Production agents layer
policy, hooks, and lifecycle controls on top.
*/

package main

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"os"

	"github.com/anthropics/anthropic-sdk-go"
	_ "github.com/anthropics/anthropic-sdk-go" // imported as anthropic
	"github.com/anthropics/anthropic-sdk-go/option"
)

var (
	ANTHROPIC_API_KEY  string
	ANTHROPIC_MODEL    string
	ANTHROPIC_BASE_URL string
)

func mustGetEnv(k, dv string) string {
	ev := os.Getenv(k)
	if ev != "" {
		return ev
	}
	if dv != "" {
		return dv
	}
	log.Fatalf("%s is not set or is empty", k)
	return ""
}

func init() {
	ANTHROPIC_API_KEY = mustGetEnv("ANTHROPIC_API_KEY", "")
	ANTHROPIC_MODEL = mustGetEnv("ANTHROPIC_MODEL", "MiniMax-M2.5")
	ANTHROPIC_BASE_URL = mustGetEnv("ANTHROPIC_BASE_URL", "https://api.minimaxi.com/anthropic")
}

func main() {
	client := anthropic.NewClient(
		option.WithAPIKey(ANTHROPIC_API_KEY),
		option.WithBaseURL(ANTHROPIC_BASE_URL),
	)
	message, err := client.Messages.New(context.TODO(), anthropic.MessageNewParams{
		MaxTokens: 1024,
		Messages: []anthropic.MessageParam{
			anthropic.NewUserMessage(anthropic.NewTextBlock("Who are you?")),
		},
		Model: anthropic.Model(ANTHROPIC_MODEL),
	})
	if err != nil {
		panic(err.Error())
	}

	s, err := json.MarshalIndent(message, "", "  ")
	if err != nil {
		panic(err.Error())
	}
	fmt.Println(string(s))
}
