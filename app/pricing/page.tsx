"use client"

import { useState, useEffect } from "react"
import Link from "next/link"
import { ArrowLeft, Check, Sparkles, Zap, Bot } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { getModelsRich, type ModelRichInfo } from "@/lib/api"

export default function PricingPage() {
  const [models, setModels] = useState<ModelRichInfo[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getModelsRich().then(setModels).catch(console.error).finally(() => setLoading(false))
  }, [])

  const getIcon = (provider: string) => {
    switch(provider) {
        case 'openai': return <Zap className="w-4 h-4 text-green-500" />
        case 'anthropic': return <Bot className="w-4 h-4 text-orange-500" />
        case 'gemini': return <Sparkles className="w-4 h-4 text-blue-500" />
        default: return <Sparkles className="w-4 h-4" />
    }
  }

  if (loading) {
    return <div className="flex justify-center items-center h-screen">Loading...</div>
  }

  return (
    <div className="min-h-screen bg-background p-8">
      <div className="max-w-5xl mx-auto space-y-8">
        
        {/* Header */}
        <div className="flex items-center gap-4">
            <Link href="/">
              <Button variant="ghost" size="icon">
                <ArrowLeft className="w-4 h-4" />
              </Button>
            </Link>
            <div>
              <h1 className="text-3xl font-bold">Models & Pricing</h1>
              <p className="text-muted-foreground">Transparent token costs for all available models.</p>
            </div>
        </div>

        {/* Models Table */}
        <Card>
            <CardHeader>
                <CardTitle>Token Consumption Rates</CardTitle>
                <CardDescription>Cost per 1,000 tokens (approx 750 words).</CardDescription>
            </CardHeader>
            <CardContent>
                <Table>
                    <TableHeader>
                        <TableRow>
                            <TableHead>Model</TableHead>
                            <TableHead>Tier</TableHead>
                            <TableHead>Input Cost / 1k</TableHead>
                            <TableHead>Output Cost / 1k</TableHead>
                            <TableHead className="text-right">Description</TableHead>
                        </TableRow>
                    </TableHeader>
                    <TableBody>
                        {models.map((model) => (
                            <TableRow key={model.value}>
                                <TableCell className="font-medium flex items-center gap-2">
                                    {getIcon(model.provider)}
                                    {model.label}
                                </TableCell>
                                <TableCell>
                                    <Badge variant={model.tier === 'free' ? 'secondary' : 'default'} className="uppercase text-[10px]">
                                        {model.tier}
                                    </Badge>
                                </TableCell>
                                <TableCell>${model.input_cost.toFixed(5)}</TableCell>
                                <TableCell>${model.output_cost.toFixed(5)}</TableCell>
                                <TableCell className="text-right text-muted-foreground text-xs">
                                    {model.description}
                                </TableCell>
                            </TableRow>
                        ))}
                    </TableBody>
                </Table>
            </CardContent>
        </Card>

        {/* Tiers Info */}
        <div className="grid md:grid-cols-2 gap-6">
            <Card className="border-2 border-muted bg-muted/20">
                <CardHeader>
                    <CardTitle>Free Tier</CardTitle>
                    <CardDescription>For casual users and testing.</CardDescription>
                </CardHeader>
                <CardContent className="space-y-2 text-sm">
                    <div className="flex gap-2"><Check className="w-4 h-4 text-green-500"/> Access to GPT-3.5 Turbo</div>
                    <div className="flex gap-2"><Check className="w-4 h-4 text-green-500"/> Access to Gemini Flash</div>
                    <div className="flex gap-2"><Check className="w-4 h-4 text-green-500"/> 5,000 monthly tokens</div>
                </CardContent>
            </Card>

            <Card className="border-2 border-primary/20 bg-primary/5">
                <CardHeader>
                    <CardTitle className="text-primary">Pro Tier</CardTitle>
                    <CardDescription>Power users needing intelligence.</CardDescription>
                </CardHeader>
                <CardContent className="space-y-2 text-sm">
                    <div className="flex gap-2"><Check className="w-4 h-4 text-primary"/> <strong>GPT-4o & Claude 3.5 Sonnet</strong></div>
                    <div className="flex gap-2"><Check className="w-4 h-4 text-primary"/> Gemini Pro 1.5</div>
                    <div className="flex gap-2"><Check className="w-4 h-4 text-primary"/> 100,000 monthly tokens</div>
                </CardContent>
            </Card>
        </div>

      </div>
    </div>
  )
}