"use client"

import { BookOpen, BrainCircuit, Boxes, ClipboardList, Database, HelpCircle, PackageOpen, ShieldCheck, Wrench } from "lucide-react"
import { Header } from "@/components/dashboard/header"
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion"
import { Card } from "@/components/ui/card"

const modules = [
  { icon: Boxes, title: "Parc informatique", text: "Ajoutez les équipements, suivez leur état, leur service, leur localisation et leur cycle de vie." },
  { icon: ClipboardList, title: "Demandes", text: "Déclarez une panne, définissez sa priorité puis suivez sa validation et son affectation." },
  { icon: Wrench, title: "Interventions", text: "Renseignez le diagnostic, les actions, la solution, les tests, les coûts et les changements de statut." },
  { icon: PackageOpen, title: "Stock", text: "Gérez les pièces, les seuils et tous les mouvements d’entrée, de sortie, de retour ou d’inventaire." },
  { icon: BrainCircuit, title: "Intelligence artificielle", text: "Recherchez les cas historiques similaires et calculez un score de risque explicable par équipement." },
  { icon: Database, title: "Historique et BI", text: "Les données Excel seront importées dans PostgreSQL après audit et alimenteront les analyses et Power BI." },
]

export function HelpContent() {
  return (
    <>
      <Header title="Centre d’aide" description="Comprenez le fonctionnement de la plateforme et le rôle de chaque module." />
      <div className="mt-5 space-y-4">
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {modules.map((item) => <Card key={item.title} className="p-5 shadow-sm transition-all hover:-translate-y-0.5 hover:shadow-lg"><div className="mb-4 flex h-11 w-11 items-center justify-center rounded-2xl bg-primary/10 text-primary"><item.icon className="h-5 w-5" /></div><h2 className="font-semibold">{item.title}</h2><p className="mt-2 text-sm leading-relaxed text-muted-foreground">{item.text}</p></Card>)}
        </div>

        <Card className="overflow-hidden border-border/80 bg-card shadow-sm">
          <div className="flex items-center gap-3 border-b p-5"><div className="rounded-xl bg-primary/10 p-3 text-primary"><BookOpen className="h-5 w-5" /></div><div><h2 className="font-semibold">Questions fréquentes</h2><p className="text-xs text-muted-foreground">Règles importantes du fonctionnement métier</p></div></div>
          <div className="p-5">
            <Accordion type="single" collapsible className="w-full">
              <AccordionItem value="q1"><AccordionTrigger>Pourquoi une demande et une intervention sont-elles séparées ?</AccordionTrigger><AccordionContent>La demande représente le problème déclaré par un utilisateur. L’intervention représente le travail technique réalisé pour diagnostiquer et résoudre ce problème. Cette séparation améliore la traçabilité.</AccordionContent></AccordionItem>
              <AccordionItem value="q2"><AccordionTrigger>Pourquoi une intervention ne peut-elle pas être clôturée immédiatement ?</AccordionTrigger><AccordionContent>Le backend exige un diagnostic, une solution et un résultat de test avant le statut « Terminée ». Cette règle évite les clôtures incomplètes et améliore la qualité de l’historique.</AccordionContent></AccordionItem>
              <AccordionItem value="q3"><AccordionTrigger>Comment fonctionne l’alerte de stock ?</AccordionTrigger><AccordionContent>Une pièce est considérée en stock faible lorsque sa quantité disponible devient inférieure ou égale au seuil minimal défini dans sa fiche.</AccordionContent></AccordionItem>
              <AccordionItem value="q4"><AccordionTrigger>Les suggestions IA sont-elles des décisions automatiques ?</AccordionTrigger><AccordionContent>Non. Elles assistent le technicien et le responsable à partir des données historiques. La validation et la décision finale restent humaines.</AccordionContent></AccordionItem>
              <AccordionItem value="q5"><AccordionTrigger>Où seront stockées les données historiques Excel ?</AccordionTrigger><AccordionContent>Le fichier brut restera intact. Les données seront importées dans un schéma de staging PostgreSQL, nettoyées puis transformées vers des tables analytiques utilisées par le dashboard, l’IA et Power BI.</AccordionContent></AccordionItem>
            </Accordion>
          </div>
        </Card>

        <Card className="flex flex-col gap-4 bg-primary p-5 text-primary-foreground shadow-lg sm:flex-row sm:items-center sm:justify-between"><div className="flex items-start gap-3"><ShieldCheck className="mt-0.5 h-6 w-6" /><div><h2 className="font-semibold">Bonnes pratiques</h2><p className="mt-1 text-sm text-primary-foreground/75">Utilisez des descriptions précises, mettez à jour les statuts au bon moment et ne partagez jamais les clés secrètes ou mots de passe.</p></div></div><HelpCircle className="hidden h-10 w-10 opacity-30 sm:block" /></Card>
      </div>
    </>
  )
}
