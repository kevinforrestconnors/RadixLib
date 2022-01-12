from typing import Dict, Optional, List, Union
from .provider import Provider
from .network import Network
from .signer import Signer
from .action import Action
import requests
import json
import re


class Wallet():
    """ 
    A class which connects a provider with a wallet and allows for transactions to be
    made using this given wallet through the supplied provider.

    The whole concept and idea behind this wallet object is that I would like for it to
    be more abstract and higher level than the basic provider implementation.
    """

    def __init__(
        self,
        provider: Provider,
        signer: Signer,
        index: int = 0
    ) -> None:
        """ 
        Instatiates a new Radix object through the provider and the signer objects passed
        to the object.

        # Arguments

        * `provider: Provider` - A provider object which connects to the Radix blockchain RPC
        API.
        * `signer: Signer` - A signer object which stores the public and private keys for the 
        given radix wallet.
        """

        self.__provider: Provider = provider
        self.__signer: Signer = signer
        self.__index: int = index
    
    @property
    def provider(self) -> Provider:
        """ A getter method for the Raidx provider. """
        return self.__provider

    @property
    def signer(self) -> Signer:
        """ A getter method for the Radix signer """
        return self.__signer

    @property
    def index(self) -> int:
        """ A getter method for the given index """
        return self.__index

    def get_balances(self) -> Dict[str, int]:
        """ 
        This method queries the blockchain for the balances of the tokens that this person
        holds and returns a dictionary mapping of the token RRI and the balance of this token.

        # Returns

        * `Dict[str, int]` - A dictionary mapping which maps the RRI to the balance of the tokens
        """

        response: dict = self.provider.get_balances(
            address = self.signer.wallet_address(
                index = self.index,
                mainnet = True if self.provider.network is Network.MAINNET else False
            )
        ).json()

        if 'error' in response.keys():
            raise KeyError(f"Encountered an error when trying to get the balances: {response}")

        return {
            token_info['rri']: int(token_info['amount'])
            for token_info in response['result']['tokenBalances']
        }

    def get_balance_of_token(
        self,
        token_rri: str
    ) -> int:
        """
        Gets the balance for the specific token with the provided RRI.

        # Arguments

        * `token_rri: str` - A string of the token RRI to get the balance of

        # Returns

        * `int` - An integer of the current balance for the provided token
        """

        balance: int = self.get_balances().get(token_rri)
        
        return 0 if balance is None else balance

    def build_sign_and_send_transaction(
        self,
        actions: Union[Action, List[Action]],
        fee_payer: str,
        message: Optional[str] = None,
        encrypt_message: bool = False,
    ) -> str:
        """
        A method which is used to build, sign, and then eventually send a transaction
        off to the blockchain. This method is used as a quick and higher level way to 
        make transactions.

        # Arguments

        * `actions: Union[Action, List[Action]]` - A list of the `Radix.Action` objects which we want to incldue in
        the transaction
        * `fee_payer: str` - A string of the address which will be paying the fees of the transaction.
        * `message: Optional[str]` - A message to include in the transaction.
        * `encrypt_message: bool` - A boolean which defines if the message included in the transaction should be 
        encrypted or not. The encryption used makes it so that only the wallet of the receiver can decode.

        # Returns

        * `str` - A string of the transaction hash for this transaction.

        # Raises

        * `KeyError` - A key error if any error is faced during the building, signing, or the sending of the 
        transaction.
        """

        # Building the transaction through the data passed to the function
        response: dict = self.provider.build_transaction(
            actions = actions,
            fee_payer = fee_payer,
            message = message,
        ).json()

        if 'error' in response.keys():
            raise KeyError(f"An error was encountered while building the transaction. Error: {response}")

        # Signing the transaction information
        blob: str = response['result']['transaction']['blob']
        hash_of_blob_to_sign: str = response['result']['transaction']['hashOfBlobToSign']
        signed_data: str = self.signer.sign(hash_of_blob_to_sign, index = self.index)

        # Finalizing the transaction and sending it
        response: requests.Response = self.provider.finalize_transaction(
            blob = blob,
            signature_der = signed_data,
            public_key_of_signer = self.signer.public_key(index = self.index),
            immediateSubmit = True
        ).json()

        if 'error' in response.keys():
            raise Exception(f"An error has occured when finalizing the transaction: {response['error']}")

        try:
            return response['result']['txID']
        except:
            return response['result']['transaction']['txID']