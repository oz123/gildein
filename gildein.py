#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
""" 
   
   gildein.py 

   for example:  ./gildein.py -c transexample.csv -o homeBank.csv 

   This is a little script to convert CSV file from DeutscheBank to
   HomeBank format. 
   However, the script is written in such a way that you could easily
   modify it and use it to convert CSV files from other banks. 
   
   See the example rcfile, where you can specify your own CSV structure. 

#  Copyright 2012 Oz N <nahumoz__AT_NONONO_SPAMHERE g m a i l dot com>
#  
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#  
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#  
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.
#  
"""


import ConfigParser,csv,sys
import os
from optparse import OptionParser
import sys

class MyConfigParser(ConfigParser.ConfigParser):
    """
    redfine ConfigParser so we have an option to write a section
    with a seperator other than equal sign. 
    """
    def write(self, fp, separator='='):
        """use different sign as separator, overiding default equal"""      
        if self._defaults:
            fp.write("[%s]\n" % DEFAULTSECT)
            for (key, value) in self._defaults.items():
                fp.write("%s %s %s\n" % (key, separator \
                ,str(value).replace('\n', '\n\t')))
            fp.write("\n")
        for section in self._sections:
            fp.write("[%s]\n" % section)
            for (key, value) in self._sections[section].items():
                if key == "__name__":
                    continue
                if (value is not None) or (self._optcre == self.OPTCRE):
                    sep = " "+separator+" "
                    key = sep.join((key, str(value).replace('\n', '\n\t')))
                fp.write("%s\n" % (key))
            fp.write("\n")
    def writesection(self, fp, section, separator='='):
        """write a single section"""
        fp.write("[%s]\n" % section)
        for (key, value) in self._sections[section].items():
            if key == "__name__":
                continue
            if (value is not None) or (self._optcre == self.OPTCRE):
                sep = " "+separator+" "
                key = sep.join((key, str(value).replace('\n', '\n\t')))
                fp.write("%s\n" % (key))
        fp.write("\n")



class Converter(object):
    """
    Create an object to convert the CSV from DB to HomeBank
    """
    def run(self, cfgfname,csvfname,outfname):
        self.cfg = self.getConfig(cfgfname)
        self.categories = self.parseSection('categories')
        self.payees = self.parseSection('payees')
        
        self.incsvformat = self.cfg.get('general','format') 
        
        self.descColumn = int(self.cfg.get(self.incsvformat,'descColumn')) #2
        self.dateColumn = int(self.cfg.get(self.incsvformat,'dateColumn')) #1
        self.inComeColumn = int(self.cfg.get(self.incsvformat,'incomecolumn')) #4
        self.outComeColumn = int(self.cfg.get(self.incsvformat,'outcomecolumn')) #3
        
        self.csvDB = self.openDBankCSV(csvfname)
        newCSV = [["date", "paymode", "info", "payee", "description",
        "amount","category"]]*len(self.csvDB)
        for index, item in enumerate(self.csvDB):
            Found, income = False, False
            self.description=item[0][self.descColumn]
            date = item[0][self.dateColumn]
            if item[0][self.outComeColumn]:
                amount = item[0][self.outComeColumn]
                income = False
            else:
                amount = item[0][self.inComeColumn]
                income = True
            paymode = self.cfg.get('general','defaultpaymode') 
            payee = self.cfg.get('general','defaultpayee')
            self.categories, cat = self.matchKey( self.categories, 'categories') 
            if income:
                self.payees, payee = self.matchKey( self.payees, 'payees') 
            newCSV[index] = [ date, paymode,'INFO WAS NOT ENTERED', payee, \
            self.description, amount ,cat ] 
            #raw_input('Enter to continue...')
        with open(outfname,'w') as newdb:
            writer = csv.writer(newdb, delimiter=';')
            writer.writerows(newCSV)
        self.updateCategories(self.categories, cfgfname)
        return 0   
        
    def matchKey(self, sectionDict, sectionName):
        Found = False
        for key in sectionDict.keys():
            if key.lower() in self.description.lower():
                match = sectionDict[key]
                Found = True
                break
        if not Found:
            print "Did not find a match for ", self.description
            ans = raw_input("Would you like to enter a new keyword for %s? [Y/n]" % sectionName )
            if ans == "" or ans.lower() == "y":
                print "Please enter a of keyword and the %s matching:" % sectionName
                newkey = raw_input("Enter keyword:")
                newval = raw_input("Enter %s:" % sectionName )
                sectionDict[newkey] = newval
                #sectionDict, match = self.addCategory(sectionDict)
                match = newkey
            else: match = ''
        return sectionDict, match
        
    def getConfig(self,fname):
        """read configuration"""
        cfg = MyConfigParser()
        #print os.listdir(os.environ["HOME"]+'/.config/gildein/')
        try:
            f=open(fname)
            cfg.readfp(f)
            return cfg
        except IOError:
            print "Could not find config file in: ", fname
            sys.exit(1)

    def parseSection(self,sectionName):
        """
        Parse section like categories or payees, return dictionary
        multiple keys can have the same value !!! 
        not the other way round ...
        """
        try: 
            self.items=self.cfg.items(sectionName)        
            self.items=dict(self.items)
            d = {}
            for v,k in self.items.iteritems():
                if "," in k:
                    keys = k.split(",")
                    for key in keys:
                        key = key.strip(" ")
                        d[key]=v
                else: 
                    d[k] = v
            return d
        except ConfigParser.NoSectionError:
            self.cfg.add_section(sectionName)
            print "WARNING: Added section ", sectionName
            d = {}
            return d  
        
    def openDBankCSV(self, fname):
        """open the DB CSV and read into a list"""
        # todo allow cusomization here, specify number
        # of rows to skip and number of rows to chomp in the end
        try:
            with open(fname,"r") as f:        
                reader = csv.reader(f, delimiter = ";")
                for i in range(5):
                    next(f)
                trans = zip(reader)
            # remove the last line as it is not necessary
            trans = trans[:-1]
            return trans
        except IOError:
            print "No such input file: ", fname
            sys.exit(1) 

    def editPayee(self, amount, description):
        """read payee from std, later we should have categories also..."""
        print "%s was paid according to %s" % (amount, description)
        payee = raw_input('Enter the name of the payee: ')
        return payee

    def updateCategories(self,d,cfgName):
        """
        write the categories dictionary into a file before existing
        d - dictionary of exsiting categories
        """
        values= list(set(d.values()))
        newCategories = {}
        #make new dictionary, where the old values are keys
        for val in values:
            newCategories[val] = ''
        #assign the values to the new dictionary
        for val in values:
            for key in d.keys():
                if d[key] == val:
                    newCategories[val]=newCategories[val]+key+", "
        for k,v in newCategories.iteritems():
            self.cfg.set('categories', k,v.strip(", "))
        with open(cfgName, 'w+') as configfile:
            for section in self.cfg.sections():
                if section == 'categories':
                    configfile.write('# category name: keywords spearated' \
                    + 'by commas\n')
                    self.cfg.writesection(configfile, section, separator=':')
                else:
                    self.cfg.writesection(configfile, section)

    
def main():
    version = "Gildein 0.1 Copyright Oz Nahum <nahumoz re.sub(bet,at) gmail dot com>"
    parser = OptionParser(usage="usage: %prog [options] filename\n%prog -h to see help")
    parser.add_option("-i", "--input",
                      action="store_true",
                      dest="inputfile",
                      help="Path to the CSV input file ")
    parser.add_option("-o", "--output",
                      action="store", # optional because action defaults to "store"
                      dest="output",
                      default="converted.csv",
                      help="Path to formated output file (default: convertrd.csv)")
    parser.add_option("-v", "--version",action="store_true", 
                        dest="version",
                        help="Show version and exit",
                        default=False)
    parser.add_option("-c","--convert", action="store", dest="inputfile")
    parser.add_option("-n","--noise", action="store_true", help="make noise", dest="noise")
    parser.add_option("-r","--rcfile", action="store",  
                        help="specify custom config file," \
                        +"Default: ~/.confing/gildein/gildeinrc", 
                        dest="config")
    (options, args) = parser.parse_args()
    
    if options.version:
        print version
        sys.exit(0)
    if options.noise:
        print "make some noisenoisenoisenoisenoisenoisenoisenoise"
        sys.exit(0)
    if options.inputfile:
        print "will convert: ", options.inputfile    
    if options.inputfile:
        if not options.output:
            out = "converted.csv"
        elif options.output:
            out = options.output
            print "will output:", options.output
        if options.config:
            config = options.config
        else: config = os.environ["HOME"] + '/.config/gildein/gildeinrc'
        print "config file is:", config  
        a=Converter()
        a.run(config,options.inputfile,out)
    else:  parser.print_help()


# todo: replace optparse with argparse

if __name__ == '__main__':
    
    main()
    

